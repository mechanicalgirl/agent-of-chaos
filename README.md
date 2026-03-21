# agent-of-chaos

docker build --no-cache --build-arg CHAOS_LEVEL=high -t mail-test .
docker run -d -p 2222:22 --name mail-test mail-test

cli connection options:
docker exec -it mail-test bash
docker exec -it --user root mail-test service dovecot start
ssh crawler@localhost -p 2222

docker stop mail-test
docker rm mail-test
docker rmi mail-test:latest 
