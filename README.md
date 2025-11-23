# DE Quest

Submission code for the DE Quest assignment.

## Requirements

- Python 3.13
- Terraform

## Set Up

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install requirements.txt.

```bash
pip install -r requirements.txt
```

Add your AWS user access key ID, secret access key, and email to a file called .env under the root folder of the project.

```txt
ACCESS_KEY_ID = "<Insert Access Key ID>"
SECRET_ACCESS_KEY = "<Insert Secret Access Key>"
EMAIL = "<Insert Email Address for BLS API call>"
```


## Usage

### Part 1
For part 1, run the part1.py script to update the BLS data and print out links to the locations in the s3 bucket to view.
```bash
python part1.py
```
For convenience, here are the public links to the uploaded files:
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.class
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.contacts
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.data.0.Current
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.data.1.AllData
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.duration
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.footnote
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.measure
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.period
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.seasonal
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.sector
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.series
https://s3-rearc-quest-hs.s3.us-east-1.amazonaws.com/bls/pr/pr.txt

### Part 2
For part 2, run the part2.py script to update the population data and print out links to the location in the s3 bucket to view.
```bash
python part2.py
```
### Part 3
Open part3.ipynb using Jupyter Notebook and run to perform the data analysis of data from parts 1 and 2.
### Part 4
Deploy the data pipeline using terraform to schedule the data to update daily.
```bash
terraform apply
```
