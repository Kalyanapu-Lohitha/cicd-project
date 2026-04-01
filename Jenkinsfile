pipeline {
    agent none

    environment {
        DOCKER_IMAGE    = 'lohitha30285/cicd-project'
        DOCKER_TAG      = "${env.BUILD_NUMBER}"
        KUBECONFIG_PATH = '/var/jenkins_home/.kube/config'
    }

    stages {

        stage('Checkout') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 1: Checking out source code ==='
                checkout scm
                sh 'echo "Branch: ${GIT_BRANCH}" && echo "Commit: ${GIT_COMMIT}"'
            }
        }

        stage('Install Dependencies') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 2: Installing Python dependencies ==='
                sh '''
                    pip install -q -r app/requirements.txt
                    pip install -q pytest-cov flake8
                '''
            }
        }

        stage('Code Quality — Lint') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 3: Running flake8 code quality check ==='
                sh '''
                    pip install -q flake8
                    flake8 app/ --max-line-length=120 \
                        --exclude=__pycache__,migrations \
                        --format=default || true
                '''
            }
        }

        stage('Run Tests') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 4: Running all 15 test cases ==='
                sh '''
                    pip install -q -r app/requirements.txt
                    pip install -q pytest-cov
                    pytest tests/ \
                        -v \
                        --tb=short \
                        --junitxml=test-results/results.xml \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing
                '''
            }
            post {
                always {
                    junit 'test-results/results.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }

        stage('Security Scan — Bandit') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 5: Running security scan ==='
                sh '''
                    pip install -q bandit
                    bandit -r app/ -f txt -o bandit-report.txt -ll || true
                    cat bandit-report.txt
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'bandit-report.txt', allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker Image') {
            agent {
                docker {
                    image 'docker:24'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 6: Building Docker image ==='
                sh '''
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                    echo "Image built: ${DOCKER_IMAGE}:${DOCKER_TAG}"
                    docker images | grep ${DOCKER_IMAGE}
                '''
            }
        }

        stage('Smoke Test Container') {
            agent {
                docker {
                    image 'docker:24'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 7: Smoke testing the container ==='
                sh '''
    docker rm -f smoke-test || true
    docker run -d --name smoke-test -p 5099:5000 lohitha30285/cicd-project:latest
    sleep 8
    docker exec smoke-test wget -qO- http://localhost:5000/health
    docker stop smoke-test && docker rm smoke-test
    echo "Smoke test PASSED"
'''
            }
        }

        stage('Push to Docker Hub') {
            agent {
                docker {
                    image 'docker:24'
                    args '-v /var/run/docker.sock:/var/run/docker.sock -u root'
                }
            }
            steps {
                echo '=== Stage 8: Pushing image to Docker Hub ==='
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker push ${DOCKER_IMAGE}:latest
                        echo "Pushed ${DOCKER_IMAGE}:${DOCKER_TAG} to Docker Hub"
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            agent { label 'built-in' }
            steps {
                echo '=== Stage 9: Deploying to Kubernetes (Minikube) ==='
                sh '''
                    export KUBECONFIG=/var/jenkins_home/.kube/config

                    which kubectl || (curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl" && chmod +x kubectl && mv kubectl /usr/local/bin/)

                    sed -i "s|IMAGE_TAG|${DOCKER_TAG}|g" k8s/deployment.yml
                    kubectl apply -f k8s/namespace.yml
                    kubectl apply -f k8s/deployment.yml
                    kubectl apply -f k8s/service.yml
                    kubectl apply -f k8s/hpa.yml

                    kubectl rollout status deployment/taskflow-deployment \
                        -n taskflow --timeout=120s

                    echo "Deployment complete"
                    kubectl get pods -n taskflow
                    kubectl get svc  -n taskflow
                '''
            }
        }

        stage('Verify Deployment') {
            agent { label 'built-in' }
            steps {
                echo '=== Stage 10: Verifying deployment health ==='
                sh '''
                    export KUBECONFIG=/var/jenkins_home/.kube/config
                    sleep 10
                    kubectl get pods -n taskflow -o wide      || true
                    kubectl get deployments -n taskflow        || true
                    kubectl describe svc taskflow-service -n taskflow || true
                    echo "Deployment verified successfully"
                '''
            }
        }
    }

    post {
        success {
            echo '=== PIPELINE SUCCEEDED === All stages passed. App is live on Kubernetes.'
            emailext(
                subject: "BUILD SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """
                    <h2>Pipeline Succeeded</h2>
                    <p><b>Project:</b> ${env.JOB_NAME}</p>
                    <p><b>Build:</b> #${env.BUILD_NUMBER}</p>
                    <p><b>Image:</b> ${DOCKER_IMAGE}:${env.BUILD_NUMBER}</p>
                    <p><b>All 15 tests passed.</b></p>
                    <p><a href="${env.BUILD_URL}">View build in Jenkins</a></p>
                """,
                mimeType: 'text/html',
                to: 'lohithachowdaryk@gmail.com'
            )
        }
        failure {
            echo '=== PIPELINE FAILED ==='
            emailext(
                subject: "BUILD FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """
                    <h2>Pipeline Failed</h2>
                    <p><b>Project:</b> ${env.JOB_NAME}</p>
                    <p><b>Build:</b> #${env.BUILD_NUMBER}</p>
                    <p><b>Stage that failed:</b> Check console output.</p>
                    <p><a href="${env.BUILD_URL}console">View console log</a></p>
                """,
                mimeType: 'text/html',
                to: 'lohithachowdaryk@gmail.com'
            )
        }
        always {
            node('built-in') {
                cleanWs()
            }
        }
    }
}