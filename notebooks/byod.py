#publish to: "TEMP-byod-edits" "test-byod-local"
import os
import callysto

# Mock the notebook environment
os.environ['WORKSPACE_NAME'] = "TEMP-byod-edits"
os.environ['WORKSPACE_BUCKET'] = "gs://fc-8e608b2e-016e-45e3-a254-4d00ad67eac0"
os.environ['GOOGLE_PROJECT'] = "anvil-stage-demo"

BLANK_CELL_VALUE = ""

with callysto.Cell("markdown"):
    """
    # Bring your own data to your Terra workspace and organize it in a data table
    *version: 2.0*
    """

with callysto.Cell("markdown"):
    """
    If you are planning to upload many files to your Terra workspace, we recommend you organize your data into a Terra
    data table. This is especially helpful when you plan to run workflows with this data because you can avoid pasting
    in the "gs://" links to every file and instead use Terra's helpful UI features.


    In this example, we introduce tools to help you:

    1. Programmatically upload data from your local machine to your Terra workspace using `gsutil cp`.

    2. Programmatically generate a data table that conatins your samples CRAM and CRAI files. The end result will look
       like this table:

    | sample_id | cram       | crai      |
    | --------- | ---------  | --------- |
    | NWD1      | NWD1.cram  | NWD1.crai |
    | NWD2      | NWD2.cram  | NWD2.crai |

    ## Assumptions
    * You are not trying to overwrite a data table that already exists  
    * Your files follow a naming convention either like this...  
    NWD119844.CRAM  
    NWD119844.CRAM.CRAI  
    ...or this:  
    NWD119844.CRAM  
    NWD119844.CRAI  

    Files that lack the extension .cram or .crai will not be added to the data table.

    # Install requirements
    Whenever `pip install`ing on a notebook on Terra, restart the kernal after the installation.

    """

with callysto.Cell("python"):
    #%pip install --upgrade --no-cache-dir terra-notebook-utils
    #%pip install --upgrade --no-cache-dir gs-chunked-io
    pass

with callysto.Cell("markdown"):
    """
    Next come imports and environmental variables.
    """

with callysto.Cell("python"):
    import io
    import os
    from uuid import uuid4
    from firecloud import fiss
    from collections import defaultdict
    from typing import Any, List, Set, Dict, Iterable
    from terra_notebook_utils import gs

    google_project = os.environ['GOOGLE_PROJECT']
    workspace = os.environ['WORKSPACE_NAME']

with callysto.Cell("markdown"):
    """
    Finally, here are the functions we'll be using for creating data tables.
    """

with callysto.Cell("python"):
    def upload_data_table(tsv):
        resp = fiss.fapi.upload_entities(google_project, workspace, tsv, model="flexible")
        resp.raise_for_status()

    def upload_rows(table: str, rows: List[Dict[str, Any]]):
        assert rows
        columns = sorted(rows[0].keys())
        tsv_data = "\t".join([f"{table}_id", *columns])
        for i, row in enumerate(rows):
            tsv_data += os.linesep + "\t".join([f"{i}", *[row[c] for c in columns]])
        upload_data_table(tsv_data)

    def upload_columns(table: str, columns: Dict[str, List[Any]]):
        column_headers = sorted(columns.keys())
        number_of_rows = len(columns[set(columns.keys()).pop()])
        tsv_data = "\t".join([f"{table}_id", *column_headers])
        for i in range(number_of_rows):
            tsv_data += os.linesep + "\t".join([f"{i}", *[columns[h][i] for h in column_headers]])
        upload_data_table(tsv_data)

    def parse_cram_crai(filename: str):
        sample, ext = filename.str.rsplit(".", 1)
        return sample, ext

    def create_cram_crai_table(table: str, listing: Iterable[str]):
        crams = dict()
        crais = dict()
        for key in listing:
            _, filename = key.rsplit("/", 1)
            sample, ext = parse_cram_crai(filename)
            if "cram" == ext:
                crams[sample] = key
            elif "crai" == ext:
                crais[sample] = key
            else:
                continue
        samples = sorted(crams.keys())
        if len(crams) != len(crais):
            # Finding intersections can take time, so we only do this if needed
            common_samples = set(crams.keys()).intersection(set(crais.keys()))
            unmatched_crams = set(crams.keys()).difference(set(crais.keys()))
            unmatched_crais = set(crais.keys()).difference(set(crams.keys()))
            if unmatched_crams:
                warnings.warn("Crams missing crais for samples {unmatched_crams}")
            if unmatched_crais:
                warnings.warn("Crais missing crams for samples {unmatched_crais}")
            upload_columns(table, dict(sample=common_samples,
                                       cram=[crams[s] for s in common_samples],
                                       crai=[crais[s] for s in common_samples]))
        else:
            upload_columns(table, dict(sample=samples,
                                       cram=[crams[s] for s in samples],
                                       crai=[crais[s] for s in samples]))

with callysto.Cell("markdown"):
    """
    # Upload to your bucket with gsutil

    ## Install gsutil as directed by this [document](https://support.terra.bio/hc/en-us/articles/360024056512-Uploading-to-a-workspace-Google-bucket#h_01EGP8GR3G10SKRXAC7H1ENXQ3).
    Use the option "Set up gsutil on your local computer (step-by-step install)" which will allow you to upload files 
    from your computer directly to Terra. (Those familiar with Terra are aware that files can also be uploaded by
    simply dragging them in to the "Files" section in the Data tab, but as `gsutil` can upload more than one file at
    a time and has additional error handling, it is recommended to use it over dragging.) But before you can upload, 
    we will need to perform a few quick tasks.

    ### Find the path to this workspace bucket
    Using the os package, you can print your workspace bucket path.
    """

with callysto.Cell("python"):
    bucket = os.environ["WORKSPACE_BUCKET"]
    print(bucket)
with callysto.Cell("markdown"):
    """
    ### Add a prefix to your bucket path to organize your data
    In this example, we add the prefix 'my-crams'. In the terminal of your computer, you will call something like:

    `gsutil cp /Users/my-cool-username/Documents/Example.cram gs://your_bucket_info/my-crams/`

    We will be calling what comes after your bucket info, here represented as `my-crams`, as your sudirectory. We'll be
    using that subdirectory name later on, so let's make note of it here.

    """
with callysto.Cell("python"):
    subdirectory = "my-crams"
with callysto.Cell("markdown"):
    """
    #### A note on subdirectories
    Subdirectories are not true directories. If all files in a subdirectory are deleted, it will cease to exist. That is
    to say, Google Cloud does not have any equivalent to empty folders. If you would like to know more, [Google has
    documentation on its filesystem's inner workings](https://cloud.google.com/storage/docs/gsutil/addlhelp/HowSubdirectoriesWork), 
    but most users will not need to know the details.

    ## Begin the upload
    Now that you know what you will name your subdirectory, turn back to your computer's terminal and upload the data
    using `gsutil cp`. Remember you may have to log into to your Google account before using gsutil into your
    workspace bucket -- you can do so with `gcloud auth` as described in [Google's documentation](https://cloud.google.com/sdk/gcloud/reference/auth/login).

    ## Preview the data in your workspace bucket
    Let's first look at the top of the workspace bucket. This will match what you see if you go the "data" tab of
    your Terra workspace and click "Files" under the heading "OTHER DATA." There will be one directory per WDL workflow
    that has executed. You will also see your subdirectory. However, if you have imported data 
    tables from Gen3, they will not show up here, as the files within are only downloaded when their associated
    TSV tables are called upon by workflows or iPython notebooks.
    """

with callysto.Cell("python"):
    #%gsutil ls {bucket}
    pass

with callysto.Cell("markdown"):
    """
    Now, let's take a peek inside the subdirectory, where you can see all of the files you uploaded from your local
    machine.
    """

with callysto.Cell("python"):
    fulldir = bucket + "/" + subdirectory
    #!gsutil ls $fulldir

with callysto.Cell("markdown"):
    """
    # Generate a data table that links to the data in your workspace bucket

    To generate a Terra data table associating crams, crais, and sample ids (e.g. "NWD1") from the data in your bucket, 
    use the snippet:
    ```
    listing = [key for key in gs.list_bucket("my-crams")]
    create_cram_crai_table("my-table-name", listing)
    ```

    For example, the listing
    ```
    gs://my-workspace-bucket/my-crams/NWD1.cram
    gs://my-workspace-bucket/my-crams/NWD1.crai
    gs://my-workspace-bucket/my-crams/NWD2.cram
    gs://my-workspace-bucket/my-crams/NWD2.crai
    gs://my-workspace-bucket/my-crams/NWD3.cram
    gs://my-workspace-bucket/my-crams/NWD3.crai
    ```
    would produce a table that looks like this in Terra.

    | sample_id | cramLocation       | craiLocation      |
    | --------- | -----------------  | ----------------- |
    | NWD1      | NWD1.cram          | NWD1.crai         |
    | NWD2      | NWD2.cram          | NWD2.crai         |
    | NWD3      | NWD3.cram          | NWD3.crai         |

    However, the actual raw data generated will be more like this:

    | entity:sample_id | cramLocation                                  | craiLocation                                |
    | ---------        | --------------------------------------------  | ------------------------------------------- |
    | NWD1             | gs://my-workspace-bucket/my-crams/NWD1.cram   | gs://my-workspace-bucket/my-crams/NWD1.crai |
    | NWD2             | gs://my-workspace-bucket/my-crams/NWD2.cram   | gs://my-workspace-bucket/my-crams/NWD2.crai |
    | NWD3             | gs://my-workspace-bucket/my-crams/NWD3.cram   | gs://my-workspace-bucket/my-crams/NWD3.crai |
    """

with callysto.Cell("python"):
    listing = [key for key in gs.list_bucket(subdirectory)]
    create_cram_crai_table("my-table-name", listing)
with callysto.Cell("markdown"):
    """
    Now, go check the data section of your workspace. You should see a data table with the name you have given it, 
    and that table can now act as a directory of your files.

    """

with callysto.Cell("markdown"):
    """
    # Merge data tables across sample ids

    Data tables can be joined across any column of shared values. For instance, the following tables can be joined with
    the `sample_id` column:

    | sample_id | cram       | crai      |
    | --------- | ---------  | --------- |
    | NWD1      | NWD1.cram  | NWD1.crai |
    | NWD2      | NWD2.cram  | NWD2.crai |
    | NWD3      | NWD3.cram  | NWD3.crai |

    | sample_id | first_name | last_name |
    | --------- | ---------  | --------- |
    | NWD1      | Bob        | Frank     |
    | NWD2      | Sue        | Lee       |
    | NWD3      | Adrian     | Zap       |

    | sample_id | Diabetic   |
    | --------- | ---------  |
    | NWD1      | No         |
    | NWD3      | Yes        |

    The code snippet
    ```
    join_data_tables("joined_table_name", ["cram_crai_table", "name_table", "diabetic_table"], "sample_id")
    ```
    produces the combined table

    | sample_id | cram       | crai      | first_name | last_name | Diabetic   |
    | --------- | ---------  | --------- | ---------  | --------- | ---------  |
    | NWD1      | NWD1.cram  | NWD1.crai | Bob        | Frank     | No         |
    | NWD3      | NWD3.cram  | NWD3.crai | Adrian     | Zap       | Yes        |

    Note that the row for `NWD2` is missing from the combined table since it was not present in `diabetic_table`.
    """

with callysto.Cell("markdown"):
    """
    # Additional functions
    To aid in the creation of your own data tables, we have provided some more functions for you to use and adapt.
    """

with callysto.Cell("python"):
    def iter_ents(table: str):
        resp = fiss.fapi.get_entities(google_project, workspace, table)
        resp.raise_for_status()
        for item in resp.json():
            yield item

    def iter_rows(table: str):
        for item in iter_ents(table):
            yield item['attributes']

    def get_columns(table: str) -> Dict[str, List[Any]]:
        columns = defaultdict(list)
        for row in iter_rows(table):
            for key, val in row.items():
                columns[key].append(val)
        return dict(columns)

    def delete_table(table: str):
        rows_to_delete = [dict(entityType=e['entityType'], entityName=e['name'])
                          for e in iter_ents(table)]
        resp = fiss.fapi.delete_entities(google_project, workspace, rows_to_delete)
        resp.raise_for_status()

    def get_keyed_rows(table_name: str, key_column: str) -> Dict[str, Dict[str, Any]]:
        keyed_rows = dict()
        for row in iter_rows(table_name):
            key = row[key_column]
            assert key not in keyed_rows
            keyed_rows[key] = row
            del keyed_rows[key][key_column]
        return keyed_rows

    def keyed_row_columns(keyed_rows: Dict[str, Any]) -> Set[str]:
        if keyed_rows:
            random_key = set(keyed_rows.keys()).pop()
            return set(keyed_rows[random_key].keys())
        else:
            return set()

    def join_keyed_rows(keyed_rows_a: Dict[str, Any], keyed_rows_b: Dict[str, Any]) -> Dict[str, Any]:
        a_columns = keyed_row_columns(keyed_rows_a)
        b_columns = keyed_row_columns(keyed_rows_b)
        assert not a_columns.intersection(b_columns), "Keyed rows to join may not share columns"
        common_keys = set(keyed_rows_a.keys()).union(set(keyed_rows_b.keys()))
        return {k: dict(**keyed_rows_a.get(k, {c: BLANK_CELL_VALUE for c in a_columns}),
                        **keyed_rows_b.get(k, {c: BLANK_CELL_VALUE for c in b_columns}))
                for k in common_keys}

    def join_data_tables(new_table: str, tables_to_join: list, join_column: str):
        keyed_rows = get_keyed_rows(tables_to_join[0], join_column)
        for table_name in tables_to_join[1:]:
            keyed_rows = join_keyed_rows(keyed_rows, get_keyed_rows(table_name, join_column))
        upload_rows(new_table, [{join_column: k, **row} for k, row in keyed_rows.items()])

################################################ TESTS ################################################ noqa
BLANK_CELL_VALUE = f"{uuid4()}"

delete_table("test_cram_crai_table")
listing = list()
for i in range(5):
    listing.append(f"gs://some-bucket/some-pfx/sample_id_{i}.cram")
    listing.append(f"gs://some-bucket/some-pfx/sample_id_{i}.crai")
for i in range(5, 8):
    listing.append(f"gs://some-bucket/some-pfx/sample_id_{i}.cram")
    listing.append(f"gs://some-bucket/some-pfx/sample_id_{i}.cram.crai")
create_cram_crai_table("test_cram_crai_table", listing)
cram_crai_keyed_rows = get_keyed_rows("test_cram_crai_table", "sample")
for i in range(5):
    assert cram_crai_keyed_rows[f'sample_id_{i}'] == dict(cram=f"gs://some-bucket/some-pfx/sample_id_{i}.cram",
                                                          crai=f"gs://some-bucket/some-pfx/sample_id_{i}.crai")
for i in range(5, 8):
    assert cram_crai_keyed_rows[f'sample_id_{i}'] == dict(cram=f"gs://some-bucket/some-pfx/sample_id_{i}.cram",
                                                          crai=f"gs://some-bucket/some-pfx/sample_id_{i}.cram.crai")

delete_table("test_metadata_table_a")
test_metadata_table_a_columns = dict(sample=["sample_id_1", "sample_id_2", "sample_id_3", "sample_id_4"],
                                     firstname=["a", "b", "c", "d"],
                                     birthday=["e", "f", "g", "h"])
upload_columns("test_metadata_table_a", test_metadata_table_a_columns)

delete_table("test_metadata_table_b")
test_metadata_table_b_columns = dict(sample=["sample_id_1", "sample_id_2", "sample_id_3", "sample_id_5"],
                                     alpha=["1", "2", "3", "4"],
                                     beta=["5", "6", "7", "8"])
upload_columns("test_metadata_table_b", test_metadata_table_b_columns)

delete_table("test_joined_table")
join_data_tables("test_joined_table", ["test_cram_crai_table", "test_metadata_table_a", "test_metadata_table_b"], "sample")
keyed_rows = get_keyed_rows("test_joined_table", "sample")
test_metadata_a_keyed_rows = get_keyed_rows("test_metadata_table_a", "sample")
test_metadata_b_keyed_rows = get_keyed_rows("test_metadata_table_b", "sample")
assert set(keyed_rows.keys()) == {f"sample_id_{i}" for i in range(8)}

for i in range(8):
    sample = f"sample_id_{i}"
    expected_row = dict(cram=cram_crai_keyed_rows[sample]['cram'],
                        crai=cram_crai_keyed_rows[sample]['crai'],
                        firstname=test_metadata_a_keyed_rows.get(sample, dict()).get('firstname', BLANK_CELL_VALUE),
                        birthday=test_metadata_a_keyed_rows.get(sample, dict()).get('birthday', BLANK_CELL_VALUE),
                        alpha=test_metadata_b_keyed_rows.get(sample, dict()).get('alpha', BLANK_CELL_VALUE),
                        beta=test_metadata_b_keyed_rows.get(sample, dict()).get('beta', BLANK_CELL_VALUE))
    assert expected_row == keyed_rows[sample]
