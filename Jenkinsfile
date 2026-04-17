pipeline {
    agent any

    environment {
        DOCKER_HUB_USER = 'diksha'
        DOCKER_IMAGE_FW = "${DOCKER_HUB_USER}/firewall-service"
        DOCKER_IMAGE_SW = "${DOCKER_HUB_USER}/switch-service"
        DOCKER_IMAGE_MN = "${DOCKER_HUB_USER}/monitor-service"
    }

    stages {

        stage('Clone Repository') {
            steps {
                checkout scm
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    cd firewall-service
                    pip install -r requirements.txt
                    python -m pytest tests/ -v
                '''
                sh '''
                    cd switch-service
                    pip install -r requirements.txt
                    python -m pytest tests/ -v
                '''
                sh '''
                    cd monitor-service
                    pip install -r requirements.txt
                    python -m pytest tests/ -v
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                sh "docker build -t ${DOCKER_IMAGE_FW}:latest ./firewall-service"
                sh "docker build -t ${DOCKER_IMAGE_SW}:latest ./switch-service"
                sh "docker build -t ${DOCKER_IMAGE_MN}:latest ./monitor-service"
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh "echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin"
                    sh "docker push ${DOCKER_IMAGE_FW}:latest"
                    sh "docker push ${DOCKER_IMAGE_SW}:latest"
                    sh "docker push ${DOCKER_IMAGE_MN}:latest"
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh 'kubectl apply -f k8s/firewall-deployment.yaml'
                sh 'kubectl apply -f k8s/switch-deployment.yaml'
                sh 'kubectl apply -f k8s/monitor-deployment.yaml'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check the logs for details.'
        }
    }
}
