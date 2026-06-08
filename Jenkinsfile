// Minimal Jenkins pipeline — see docs/JENKINS_SETUP.md
//
// Jenkins credential (Global): id = dockerhub, type = Username with password
//   Username: vd0610
//   Password: Docker Hub access token

pipeline {
    agent any

    environment {
        DOCKER_USER = 'vd0610'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub',
                    usernameVariable: 'DH_USER',
                    passwordVariable: 'DH_PASS'
                )]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin

                        docker build -t $DOCKER_USER/gateway:latest   -f gateway/Dockerfile   gateway/
                        docker build -t $DOCKER_USER/auth:latest      -f auth/Dockerfile      auth/
                        docker build -t $DOCKER_USER/convertor:latest -f convertor/Dockerfile convertor/

                        docker push $DOCKER_USER/gateway:latest
                        docker push $DOCKER_USER/auth:latest
                        docker push $DOCKER_USER/convertor:latest
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                sh 'chmod +x scripts/jenkins-deploy.sh && ./scripts/jenkins-deploy.sh'
            }
        }
    }
}
