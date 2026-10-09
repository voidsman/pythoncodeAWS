pipeline {
    agent any

    environment {
        IMAGE_NAME     = "student-app"
        CONTAINER_NAME = "student-app-container"
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Build image') {
            steps { sh 'docker build -t $IMAGE_NAME .' }
        }

        stage('Stop old container') {
            steps { sh 'docker rm -f $CONTAINER_NAME || true' }
        }

        stage('Run new container') {
            steps {
                // Secret text credentials stored in Jenkins (never in git).
                withCredentials([
                    string(credentialsId: 'db-host',        variable: 'DB_HOST'),
                    string(credentialsId: 'db-user',        variable: 'DB_USER'),
                    string(credentialsId: 'db-password',    variable: 'DB_PASSWORD'),
                    string(credentialsId: 's3-bucket-name', variable: 'S3_BUCKET_NAME')
                ]) {
                    sh '''
                        set +x
                        docker run -d --name $CONTAINER_NAME \
                          --restart unless-stopped \
                          -p 5020:8000 \
                          -e DB_HOST="$DB_HOST" \
                          -e DB_USER="$DB_USER" \
                          -e DB_PASSWORD="$DB_PASSWORD" \
                          -e DB_NAME=studentdb \
                          -e S3_BUCKET_NAME="$S3_BUCKET_NAME" \
                          -e AWS_REGION=eu-north-1 \
                          $IMAGE_NAME
                        docker image prune -f
                    '''
                }
            }
        }
    }
}
