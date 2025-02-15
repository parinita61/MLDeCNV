# MLDeCNV
Machine Learning based accurate prediction of Copy Number Variation

## Prerequisites
Ensure you have the following installed on your system before proceeding:
- Anaconda/Miniconda
- Ubuntu (or any Linux-based OS with bash support)
- gcc, make, zlib1g-dev, libncurses5-dev, libbz2-dev, liblzma-dev

## Step 1: Create a Python (Conda) Environment
Create a new conda environment named `mldecnv` with Python 3.12.9.
```bash
conda create --name mldecnv python=3.12.9
```

## Step 2: Activate the Environment and Install Necessary Packages
Activate the newly created environment and install the required Python packages.
```bash
conda activate mldecnv
pip install flask scikit-learn pandas numpy xgboost
```

## Step 3: Create a `tools` Directory Inside the `static` Folder
Navigate to the `mldecnv/static/` directory and create a `tools` directory.
```bash
mkdir -p mldecnv/static/tools
cd mldecnv/static/tools/
```

## Step 4: Download and Install Samtools
Download and extract Samtools 1.21, then install it.
```bash
wget https://github.com/samtools/samtools/releases/download/1.21/samtools-1.21.tar.bz2
tar -xjf samtools-1.21.tar.bz2
rm -rf samtools-1.21.tar.bz2
cd samtools-1.21/
```
Install dependencies:
```bash
sudo apt update
sudo apt install -y gcc make zlib1g-dev libncurses5-dev libbz2-dev liblzma-dev
```
Compile and install Samtools:
```bash
./configure
make
sudo make install
```
The Samtools executable path will be:
```
mldecnv/static/tools/samtools-1.21/samtools
```

## Step 5: Download and Install Bedtools
Install Bedtools using Bioconda:
```bash
conda install -c bioconda bedtools
```
Find the Bedtools path:
```bash
whereis bedtools
```
Your Bedtools path will be something like:
```
/home/user_name/anaconda3/envs/mldecnv/bin/bedtools
```

## Step 6: Update Samtools and Bedtools Paths in `feature_extraction.sh`
Modify the `feature_extraction.sh` script (located in the `static` folder) to reflect the correct paths for Samtools and Bedtools.

Example modification inside `feature_extraction.sh`:
```bash
SAMTOOLS_PATH="mldecnv/static/tools/samtools-1.21/samtools"
BEDTOOLS_PATH="/home/user_name/anaconda3/bin/bedtools"
```

## Step 7: Run the Webserver
Navigate to the `mldecnv` directory and start the Flask application.
```bash
cd mldecnv
python app.py
```
Your MLDeCNV webserver should now be running and accessible globally.

