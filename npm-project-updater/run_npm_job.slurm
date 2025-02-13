#!/bin/bash
#SBATCH --job-name=LibioNPM
#SBATCH --output=/work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater/logs/job_output_%j.log
#SBATCH --error=/work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater/logs/job_error_%j.log
#SBATCH --time=7-00:00:00  # 7 days
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G  # Adjust memory as needed
#SBATCH --partition=cpu2023

####### Set environment variables ###############
export NVM_DIR="$HOME/.nvm"

# Install NVM if not already installed
if [ ! -d "$NVM_DIR" ]; then
    echo "🚀 [INFO] Installing NVM..." | tee -a /work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater/logs/job_output_$SLURM_JOB_ID.log
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
fi

# Load NVM
source "$NVM_DIR/nvm.sh"

# Install and use Node.js (adjust version if needed)
if ! command -v node &> /dev/null; then
    echo "🚀 [INFO] Installing Node.js..." | tee -a /work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater/logs/job_output_$SLURM_JOB_ID.log
    nvm install 18
fi

nvm use 18
echo "✅ [INFO] Using Node.js version: $(node -v)" | tee -a /work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater/logs/job_output_$SLURM_JOB_ID.log

####### Move to Project Directory #######
PROJECT_DIR="/work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater"
LOG_DIR="/work/barcomb_lab/Mahdi/Libraries.io/npm-project-updater/logs"
NODE_MODULES_DIR="$PROJECT_DIR/node_modules"

cd "$PROJECT_DIR" || exit

####### Install Node.js Dependencies (if missing) #######
if [ ! -d "$NODE_MODULES_DIR" ]; then
    echo "🚀 [INFO] Installing npm dependencies..." | tee -a "$LOG_DIR/job_output_$SLURM_JOB_ID.log"
    npm install 2>&1 | tee -a "$LOG_DIR/job_output_$SLURM_JOB_ID.log"
else
    echo "✅ [INFO] Dependencies already installed. Skipping npm install." | tee -a "$LOG_DIR/job_output_$SLURM_JOB_ID.log"
fi

####### Run Node.js Script #########################
echo "🚀 [INFO] Running index.js..." | tee -a "$LOG_DIR/job_output_$SLURM_JOB_ID.log"
node index.js 2>&1 | tee -a "$LOG_DIR/job_output_$SLURM_JOB_ID.log"
echo "✅ [SUCCESS] Script finished." | tee -a "$LOG_DIR/job_output_$SLURM_JOB_ID.log"
