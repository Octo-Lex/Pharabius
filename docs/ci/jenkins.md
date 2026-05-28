# Jenkins

Run Pharabius quality gate in Jenkins.

## Declarative Pipeline Example

```groovy
pipeline {
    agent any

    tools {
        python 'Python3.11'
    }

    stages {
        stage('Install') {
            steps {
                sh 'pip install pharabius'
            }
        }

        stage('Analyze') {
            steps {
                sh '''
                    if [ ! -d .ai-debt ]; then
                        ai-debt init
                    fi
                    ai-debt run
                '''
            }
        }

        stage('Quality Gate') {
            steps {
                sh 'ai-debt gate --max-critical 0 --max-high 10 --max-total 50'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '.ai-debt/**/*', allowEmptyArchive: true
        }
    }
}
```

## Safety Notes

- No tokens or credentials required.
- All analysis is local and deterministic.
- Reports are archived as Jenkins build artifacts.
