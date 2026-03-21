# agent-of-chaos

docker build --no-cache -t mail-test .
# docker build --build-arg CHAOS_LEVEL=high -t mail-test .
docker run -d -p 2222:22 --name mail-test mail-test

# docker exec -it mail-test bash
ssh crawler@localhost -p 2222
# install stuff, configure it messily, done
docker exec -it --user root mail-test service dovecot start

docker stop mail-test
docker rm mail-test
docker rmi mail-test:latest 
