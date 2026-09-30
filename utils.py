import pandas as pd
import os
from pathlib import Path


def read_globals_config(file_path):
    """
    read the global attributes from the xbt_config file
    """
    # Accept Path or string and resolve relative to this module
    p = Path(file_path)
    if not p.is_absolute():
        p = Path(os.path.dirname(__file__)) / p
    p = p.resolve()

    # Read the CSV file into a dictionary
    df = pd.read_csv(str(p))
    # fill any empty cells and strings with NaN
    df = df.fillna(value=pd.NA)
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    # convert the DataFrame to a dictionary of 'Attribute Name': 'Attribute Value' pairs
    global_att = {}
    for index, row in df.iterrows():
        # remove any leading or trailing whitespace from the attribute name
        att_name = row['Attribute Name'].strip()
        att_value = row['Attribute Value']
        if pd.isna(att_value):
            att_value = None
        global_att[att_name] = att_value
    return global_att

def read_variables_config(file_path):
    """
    read the variable attributes from the xbt_config file
    """
    # Read the CSV file and convert it to a DataFrame
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), file_path))
    # fill any empty cells and strings with NaN
    df = df.fillna(value=pd.NA)
    df = df.replace(r'^\s*$', pd.NA, regex=True)

    return df

