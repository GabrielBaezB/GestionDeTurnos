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
                            // Stop the build if there are Python syntax errors or undefined names
                            sh '${VENV}/bin/flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,.git,__pycache__'
                            // exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
                            sh '${VENV}/bin/flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --exclude=venv,.git,__pycache__'
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
                    echo "🐳 Building Docker Image: zeroqrobo-backend:${DOCKER_TAG}"
                    sh "docker build -t zeroqrobo-backend:${DOCKER_TAG} ."
                    sh "docker tag zeroqrobo-backend:${DOCKER_TAG} zeroqrobo-backend:latest"
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
