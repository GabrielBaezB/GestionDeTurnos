pipeline {
    agent any

    options {
        ansiColor('xterm')
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        SCANNER_HOME = tool 'sonar-scanner'
        VENV = 'venv'
        // Dynamic Docker Tag based on Build Number
        DOCKER_TAG = "v1.0.${env.BUILD_NUMBER}"
    }
    
    stages {
        stage('Setup') {
            steps {
                script {
                    echo "🚀 Starting Build ${env.BUILD_NUMBER}..."
                    sh 'python3 -m venv ${VENV}'
                    sh '${VENV}/bin/pip install --no-cache-dir -r requirements.txt'
                }
            }
        }
        
        stage('Static Analysis & Testing') {
            parallel {
                stage('Linting') {
                    steps {
                        script {
                            echo '🔍 Running Flake8...'
                            // Flake8 will read .flake8 config file for excludes and settings
                            sh '${VENV}/bin/flake8 .'
                        }
                    }
                }
                
                stage('Unit Tests') {
                    steps {
                        script {
                            echo '🧪 Running Pytest...'
                            sh '''
                                export PYTHONPATH=$PYTHONPATH:.
                                export DATABASE_URL=sqlite:///test.db
                                export SECRET_KEY=test_secret
                                ${VENV}/bin/pytest --cov=backend/app --cov-report=xml:coverage.xml --junitxml=test-results.xml
                            '''
                        }
                    }
                }
            }
        }
        
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh "${SCANNER_HOME}/bin/sonar-scanner -Dsonar.projectVersion=${DOCKER_TAG}"
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
        
        stage('Build & Package') {
            steps {
                script {
                    echo "🐳 Building Docker Image: gestiondeturnos-backend:${DOCKER_TAG}"
                    sh "docker build -t gestiondeturnos-backend:${DOCKER_TAG} ."
                    sh "docker tag gestiondeturnos-backend:${DOCKER_TAG} gestiondeturnos-backend:latest"
                }
            }
        }
    }
    
    post {
        always {
            // Archive Test Results and Coverage for Jenkins UI
            junit 'test-results.xml'
            archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
            cleanWs()
        }
        success {
            echo "✅ Build ${env.BUILD_NUMBER} Succeeded!"
        }
        failure {
            echo "❌ Build ${env.BUILD_NUMBER} Failed!"
        }
    }
}
