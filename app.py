import os
import subprocess
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session
import pandas as pd
import pickle
import shutil

app = Flask(__name__)
app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024 * 1024  # 6GB max upload limit

# Paths for input and output files
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
USER_FILES_DIR = os.path.join(BASE_DIR, 'static', 'user_files')
OUTPUT_DIR = os.path.join(BASE_DIR, 'static', 'feature_output')
RESULTS_DIR = os.path.join(BASE_DIR, 'static', 'results')
SCRIPT_PATH = os.path.join(BASE_DIR, 'static', 'feature_extraction.sh')
MODEL_PATH = os.path.join(BASE_DIR, 'static', 'models', 'XGBoost_best_model.pkl')

SAMPLE_BAM = os.path.join(BASE_DIR, 'static', 'sample_bam', 'sorted_coordinate_SRR22106536.bam')
SAMPLE_BED_COORDINATES = os.path.join(BASE_DIR, 'static', 'sample_bed_coordinates', 'sample.bed')
ARABIDOPSIS_REF_GENOME = os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_000001735.2.fasta')

# Paths to reference genomes
REFERENCE_GENOMES = {
    'arabidopsis': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_000001735.2.fasta'),
    'rice': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_001433935.1_IRGSP-1.0_genomic.fa.fasta'),
    'wheat': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_900519105.1.fasta'),
    'maize': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_902167145.1.fasta'),
    'barley': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_904849725.1.fasta'),
    'cucumber': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCF_000004075.3_Cucumber_9930_V3_genomic.fna.fasta'),
    'pomegranate': os.path.join(BASE_DIR, 'static', 'sample_ref_genome', 'GCA_007655135.2_ASM765513v2_genomic.fa.fasta'),
}

# Load the trained model
with open(MODEL_PATH, 'rb') as model_file:
    model = pickle.load(model_file)


def run_script(bam_file, bed_file, ref_genome):
    """Run the feature extraction shell script with dynamic input."""
    command = f"bash {SCRIPT_PATH} {bam_file} {bed_file} {ref_genome} {OUTPUT_DIR}"
    # Debug: Print the command being executed
    print(f"Executing command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Script failed: {command}\nError: {result.stderr}")
    return result.stdout


@app.route('/')
def index():
    """Render the index.html template for uploading files."""
    return render_template('index.html')


@app.route('/analysis')
def analysis():
    """Render the upload.html template for file upload."""
    return render_template('upload.html')


@app.route('/tutorial')
def tutorial():
    """Render the tutorial.html template."""
    return render_template('tutorial.html')


@app.route('/contact')
def contact():
    """Render the contact.html template."""
    return render_template('contact.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    bam_file = request.files.get('bamfile')
    bed_file = request.files.get('bedfile')
    reference = request.form['reference']
    custome_reference_file = request.files.get('referencefile')

    # Clear the results and feature_output directories
    for directory in [USER_FILES_DIR, RESULTS_DIR, OUTPUT_DIR]:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
        else:
            os.makedirs(directory, exist_ok=True)

    # Determine paths based on whether files are uploaded or sample files are used
    if bam_file and bam_file.filename != '':
        bam_path = os.path.join(USER_FILES_DIR, bam_file.filename)
        bam_file.save(bam_path)
    else:
        bam_path = SAMPLE_BAM

    if bed_file and bed_file.filename != '':
        bed_path = os.path.join(USER_FILES_DIR, bed_file.filename)
        bed_file.save(bed_path)
    else:
        bed_path = SAMPLE_BED_COORDINATES

    
    if custome_reference_file:
        ref_genome_path = os.path.join(USER_FILES_DIR, custome_reference_file.filename)
        custome_reference_file.save(ref_genome_path)
    else:
        ref_genome_path = REFERENCE_GENOMES[reference]
    

    # Debug: Print received files and reference
    print(f"Received files: {bam_path}, {bed_path}, Reference: {ref_genome_path}")

    # Save paths in session
    session['bam_path'] = bam_path
    session['bed_path'] = bed_path
    session['ref_genome_path'] = ref_genome_path

    # Flash message for successful upload
    flash('Files uploaded successfully. Click OK to proceed.')

    # Send success response to upload.html
    return 'success'


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    """Perform feature extraction and prediction."""
    bam_path = session.get('bam_path')
    bed_path = session.get('bed_path')
    ref_genome_path = session.get('ref_genome_path')

    if not bam_path or not bed_path or not ref_genome_path:
        flash('Missing file paths. Please upload the files again.')
        return redirect(url_for('analysis'))

    # Perform feature extraction using the shell script
    run_script(bam_path, bed_path, ref_genome_path)

    # Load the 32 features CSV for prediction
    features_file = os.path.join(OUTPUT_DIR, 'merged_32_feature_final.csv')

    # Ensure the features file exists
    if not os.path.exists(features_file):
        flash('Feature extraction failed. The features file does not exist.')
        return redirect(url_for('analysis'))

    # Read the CSV file and extract 'region' column
    df = pd.read_csv(features_file, sep='\t')
    region_df = df['region']  # Extract 'region' column
    # Extract the specified seven features
    selected_features = df[['coverage', 'meandepth', 'meanbaseq', 'meanmapq', 'insert size average',
                            'insert size standard deviation', 'percentage of properly paired reads (%)']]
    # Drop 'region' column
    df.drop(['region'], axis=1, inplace=True)

    # Predict probabilities and classes using the loaded model
    probabilities = model.predict_proba(df)
    predictions = model.predict(df)
    # Map predictions to Prediction_Type
    prediction_types = {
        0: 'Deletion',
        1: 'Duplication',
        2: 'No CNV'
    }
    prediction_type = [prediction_types[pred] for pred in predictions]

    # Create result DataFrame with 'region', 'prediction', and 'Prediction_Type' columns
    result_df = pd.DataFrame({
        'Region': region_df,
        'PredictionType': prediction_type,
        'Prediction Probability': [max(prob) for prob in probabilities],
        'Coverage': selected_features['coverage'],
        'Mean Depth': selected_features['meandepth'],
        'Mean Base Quality': selected_features['meanbaseq'],
        'Mean Map Quality': selected_features['meanmapq'],
        'Insert Size Average': selected_features['insert size average'],
        'Insert Size Standard Deviation': selected_features['insert size standard deviation'],
        'Percentage Properly Paired Reads': selected_features['percentage of properly paired reads (%)'],
    })

    prediction_results_file = os.path.join(RESULTS_DIR, 'prediction_results.csv')
    result_df.to_csv(prediction_results_file, index=False)

    return render_template('view.html', data=result_df.to_html(classes='table', index=False))


@app.route('/download_results')
def download_results():
    """Download the prediction results CSV file."""
    try:
        results_file = os.path.join(RESULTS_DIR, 'prediction_results.csv')
        return send_file(results_file, as_attachment=True, download_name='prediction_results.csv')
    except Exception as e:
        return str(e)


@app.route('/download_feature')
def download_feature():
    """Download the features."""
    try:
        results_file = os.path.join(OUTPUT_DIR, 'merged_output.csv')
        return send_file(results_file, as_attachment=True, download_name='features_output.csv')
    except Exception as e:
        return str(e)


if __name__ == "__main__":
    # Ensure the necessary directories exist
    for directory in [USER_FILES_DIR, OUTPUT_DIR, RESULTS_DIR]:
        os.makedirs(directory, exist_ok=True)

    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
