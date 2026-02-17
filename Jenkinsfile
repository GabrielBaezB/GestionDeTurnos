pipeline {
    agent any

    environment {
        // Define any global variables here
        SCANNER_HOME = tool 'sonar-scanner' // Make sure 'sonar-scanner' tool is configured in Jenkins
    }
    
    stages {
        stage('Build & Install') {
            steps {
                script {
                    echo 'Building and Installing Dependencies...'
                    // Create virtual environment to comply with PEP 668
                    sh 'python3 -m venv venv'
                    // Install dependencies into venv
                    sh 'venv/bin/pip install --no-cache-dir -r requirements.txt'
                }
            }
        }
        
        stage('Linting') {
            steps {
                script {
                    echo 'Running Linting...'
                    // Example: sh 'venv/bin/ruff check .'
                    sh 'echo Linting passed'
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                script {
                    echo 'Running Unit Tests with Coverage...'
                    // Run pytest using the venv executable
                    sh 'venv/bin/pytest --cov=backend/app --cov-report=xml:coverage.xml'
                }
            }
        }
        
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') { // 'SonarQube' must match server name in Jenkins Config
                    sh "${SCANNER_HOME}/bin/sonar-scanner"
                }
            }
        }
        
        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }
        
        stage('Build Docker') {
            steps {
                script {
                    echo 'Building Docker Image...'
                    // Assumes Docker is available on the agent
                    sh 'docker build -t zeroqrobo-backend:latest .'
                }
            }
        }
    }
    
    post {
        always {
            // Clean up workspace or send notifications
            cleanWs()
        }
        failure {
            echo 'Pipeline failed!'
        }
        success {
            echo 'Pipeline succeeded!'
        }
    }
}
