import click
import httpx
from httpx import HTTPError
import os
import json as json_
import pathlib
from urllib.parse import quote, urlencode
import time

def main():
    # ============ Base ID ============
    output_path = '.export/'

    # ============ Access Key Filename and Location ============
    access_key_filename = '.abaldwin-kgsa-airtable-token.txt'
    access_key_path = os.curdir

    # ============ Base ID ============
    base_id ='appMeePQqolbGWgZx'

    # ---- Connect to Airtable ----
    with open(f"{access_key_path}/{access_key_filename}", "r", encoding="UTF-8") as file:
        access_key = file.read()
    access_key = str(access_key)
    access_key = access_key.strip()

    export(output_path=output_path,base_id=base_id,key=access_key)

def export(
    output_path,
    base_id,
    key,
    http_read_timeout=True,
    user_agent=None,
    verbose=True
):
    "Export Airtable data to YAML file on disk"
    output = pathlib.Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    write_batch = lambda table, batch: None
    schema_data = list_tables(base_id, key, user_agent=user_agent)
    dumped_schema = json_.dumps(schema_data, sort_keys=True, indent=4)
    (output / "_schema.json").write_text(dumped_schema, "utf-8")
    tables = [table["name"] for table in schema_data["tables"]]

    for table in tables:
        records = []
        try:
            db_batch = []
            for record in all_records(
                base_id, table, key, http_read_timeout, user_agent=user_agent
            ):
                r = {
                    **{"airtable_id": record["id"]},
                    **record["fields"],
                    **{"airtable_createdTime": record["createdTime"]},
                }
                records.append(r)
                db_batch.append(r)
                if len(db_batch) == 100:
                    write_batch(table, db_batch)
                    db_batch = []
        except HTTPError as exc:
            raise click.ClickException(exc)
        write_batch(table, db_batch)
        filenames = []
        filename = "{}.json".format(table)
        dumped = json_.dumps(records, sort_keys=True, indent=4)
        (output / filename).write_text(dumped, "utf-8")
        filenames.append(output / filename)
        if verbose:
            files = ", ".join(map(str, filenames))
            print(f"Wrote {len(records)} record(s) to {files}")


def list_tables(base_id, api_key, user_agent=None):
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": "Bearer {}".format(api_key)}
    if user_agent is not None:
        headers["user-agent"] = user_agent
    return httpx.get(url, headers=headers).json()


def all_records(base_id, table, api_key, http_read_timeout, sleep=0.2, user_agent=None):
    headers = {"Authorization": "Bearer {}".format(api_key)}
    if user_agent is not None:
        headers["user-agent"] = user_agent

    if http_read_timeout:
        timeout = httpx.Timeout(5, read=http_read_timeout)
        client = httpx.Client(timeout=timeout)
    else:
        client = httpx

    first = True
    offset = None
    while first or offset:
        first = False
        url = "https://api.airtable.com/v0/{}/{}".format(base_id, quote(table, safe=""))
        if offset:
            url += "?" + urlencode({"offset": offset})
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        offset = data.get("offset")
        yield from data["records"]
        if offset and sleep:
            time.sleep(sleep)


def str_representer(dumper, data):
    try:
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    except TypeError:
        pass
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


if __name__ == "__main__":
    main()