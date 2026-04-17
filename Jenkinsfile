pipeline {
    agent any

    triggers {
        githubPush()
    }

    environment {
        DOCKER_HUB_USER = 'dknights'
        GITHUB_REPO_URL = 'https://github.com/dikshax86/NFV_SPE_MajorProject.git'
    }

    stages {

        stage('Clone Repository') {
            steps {
                git url: "${GITHUB_REPO_URL}", branch: "master"
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    cd firewall-service
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    python -m pytest tests/ -v
                '''
                sh '''
                    cd switch-service
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    python -m pytest tests/ -v
                '''
                sh '''
                    cd monitor-service
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    python -m pytest tests/ -v
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                script {
                    docker.build("${DOCKER_HUB_USER}/firewall-service", "./firewall-service")
                    docker.build("${DOCKER_HUB_USER}/switch-service", "./switch-service")
                    docker.build("${DOCKER_HUB_USER}/monitor-service", "./monitor-service")
                }
            }
        }

        stage('Push to Docker Hub') {
            steps {
                script {
                    docker.withRegistry('', 'DockerHubCred') {
                        sh "docker tag ${DOCKER_HUB_USER}/firewall-service ${DOCKER_HUB_USER}/firewall-service:latest"
                        sh "docker push ${DOCKER_HUB_USER}/firewall-service:latest"

                        sh "docker tag ${DOCKER_HUB_USER}/switch-service ${DOCKER_HUB_USER}/switch-service:latest"
                        sh "docker push ${DOCKER_HUB_USER}/switch-service:latest"

                        sh "docker tag ${DOCKER_HUB_USER}/monitor-service ${DOCKER_HUB_USER}/monitor-service:latest"
                        sh "docker push ${DOCKER_HUB_USER}/monitor-service:latest"
                    }
                }
            }
        }

        stage('Deploy using Ansible') {
            steps {
                ansiblePlaybook(
                    playbook: "ansible/playbooks/deploy-compose.yml",
                    inventory: "ansible/inventory/hosts"
                )
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
