#!/bin/bash

# Dynamic input variables
BAM_FILE=$1
BED_FILE=$2
REFERENCE_GENOME=$3
OUTPUT_DIR=$4

COVERAGE_OUTPUT="$OUTPUT_DIR/Features_samtools-coverage.csv"
GC_OUTPUT="$OUTPUT_DIR/Features_GC.csv"
STATS_OUTPUT="$OUTPUT_DIR/Features_samtools-stats.csv"
MERGED_OUTPUT="$OUTPUT_DIR/merged_output.csv"
MERGED_32_FEATURE_OUTPUT="$OUTPUT_DIR/merged_32_feature_final.csv"
SAMTOOLS_PATH=/mnt/s/parinita/final_cnv_prediction/final_cnv_prediction/server_uploads/static/tools/samtools-1.21/samtools
BEDTOOLS_PATH=/home/bibek/anaconda3/envs/mldecnv_linux/bin/bedtools
# Ensure output directory exists
mkdir -p $OUTPUT_DIR

# Command 1: samtools coverage
$SAMTOOLS_PATH index $BAM_FILE
while read -r line
do
  chr=$(echo $line | cut -d" " -f1)
  start=$(echo $line | cut -d" " -f2)
  end=$(echo $line | cut -d" " -f3)
  $SAMTOOLS_PATH coverage -r $chr:$start-$end $BAM_FILE | grep -v "#" >> $COVERAGE_OUTPUT
done < $BED_FILE

# Command 2: bedtools nuc
$BEDTOOLS_PATH nuc -fi $REFERENCE_GENOME -bed $BED_FILE > $GC_OUTPUT

# Command 3: samtools stats
python3 << END
import csv
import subprocess
import os
import pandas as pd

def calculate_stats(bam_file, bed_file, output_file):
    region_stats = {}

    with open(bed_file, 'r') as bed:
        for line in bed:
            fields = line.strip().split()
            chrom, start, end = fields[:3]
            region = f"{chrom}:{start}-{end}"

            temp_bam = f"temp_{region}.bam"
            subprocess.run(["$SAMTOOLS_PATH", "view", "-b", bam_file, region, "-o", temp_bam])

            stats_output = subprocess.run(["$SAMTOOLS_PATH", "stats", temp_bam], capture_output=True, text=True)

            region_stats[region] = parse_stats_output(stats_output.stdout)

            os.remove(temp_bam)

    with open(output_file, 'w', newline='') as csvfile:
        first_region_stats = next(iter(region_stats.values())) if region_stats else {}
        fieldnames = ["Region"] + list(first_region_stats.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        for region, stats in region_stats.items():
            writer.writerow({"Region": region, **stats})

def parse_stats_output(stats_output):
    stats_dict = {}
    lines = stats_output.split('\n')
    for line in lines:
        if line.startswith("SN"):
            fields = line.split('\t')
            stat_name = fields[1]
            stat_value = fields[2]
            stats_dict[stat_name] = stat_value
    return stats_dict

calculate_stats("$BAM_FILE", "$BED_FILE", "$STATS_OUTPUT")
END

# Command 4: Filter and format CSV files using awk
awk -F'\t' 'BEGIN{OFS="\t"} NR==1 {print "region\tpct_at\tpct_gc\tnum_A\tnum_C\tnum_G\tnum_T\tlength"} {print $1":"$2"-"$3, $4, $5, $6, $7, $8, $9, $12}' $GC_OUTPUT > ${GC_OUTPUT}b.csv

awk -F'\t' 'BEGIN {OFS="\t"; print "region\tnumreads\tcovbases\tcoverage\tmeandepth\tmeanbaseq\tmeanmapq"} {print $1":"$2"-"$3, $4, $5, $6, $7, $8, $9}' $COVERAGE_OUTPUT > ${COVERAGE_OUTPUT}b.csv

awk -F'\t' 'BEGIN{OFS="\t"} NR==1 {print "region\traw total sequences\t1st fragments\tlast fragments\treads mapped\treads mapped and paired\treads unmapped\treads properly paired\treads paired\treads MQ0\ttotal length\ttotal first fragment length\ttotal last fragment length\tbases mapped\tbases mapped (cigar)\tmismatches\terror rate\taverage length\taverage first fragment length\taverage last fragment length\taverage quality\tinsert size average\tinsert size standard deviation\tinward oriented pairs\toutward oriented pairs\tpairs with other orientation\tpairs on different chromosomes\tpercentage of properly paired reads (%)"} NR>1 {print $1, $2, $6, $7, $8, $9, $10, $11, $12, $14, $18, $19, $20, $21, $22, $25, $26, $27, $28, $29, $33, $34, $35, $36, $37, $38, $39, $40}' $STATS_OUTPUT > ${STATS_OUTPUT}b.csv

# Command 5: Merge the dataframes
python3 << END
import pandas as pd

try:
    df1 = pd.read_csv("${GC_OUTPUT}b.csv", sep="\t")
    df2 = pd.read_csv("${COVERAGE_OUTPUT}b.csv", sep="\t")
    df3 = pd.read_csv("${STATS_OUTPUT}b.csv", sep="\t")

    merged_df = pd.merge(df1, df2, on="region", suffixes=('_1', '_2'))
    merged_df = pd.merge(merged_df, df3, on="region")

    merged_df = merged_df[~merged_df.duplicated(subset="region")]

    cols = merged_df.columns.tolist()
    cols = cols[:1] + cols[2:] + [cols[1]]

    merged_df = merged_df[cols]

    merged_df.to_csv("$MERGED_OUTPUT", sep="\t", index=False)

    # Extract specific columns for merged_32_feature.csv
    columns_to_extract = [
        "region", "1st fragments", "average first fragment length", 
        "average last fragment length", "average length", "average quality", 
        "covbases", "coverage", "error rate", "insert size average", 
        "insert size standard deviation", "inward oriented pairs", 
        "last fragments", "length", "meanbaseq",
        "meandepth", "meanmapq", "num_A", "num_C", "num_G", "num_T",
        "numreads", "outward oriented pairs", "pairs on different chromosomes",
        "pct_at", "pct_gc", "percentage of properly paired reads (%)",
        "raw total sequences", "reads MQ0", "reads mapped", "reads mapped and paired",
        "reads properly paired", "reads unmapped"
    ]

    extracted_df = merged_df[columns_to_extract]
    extracted_df.to_csv("$MERGED_32_FEATURE_OUTPUT", sep="\t", index=False)

except pd.errors.EmptyDataError as e:
    print(f"Error: {e}. One or more input CSV files are empty.")
    exit(1)
END

# Cleanup intermediate files
# rm "$GC_OUTPUT"
# rm "${GC_OUTPUT}b.csv"
# rm "$COVERAGE_OUTPUT"
# rm "${COVERAGE_OUTPUT}b.csv"
# rm "$STATS_OUTPUT"
# rm "${STATS_OUTPUT}b.csv"

echo "Process completed successfully."
