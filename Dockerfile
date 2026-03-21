# Use a base image with SSH installed
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN echo "postfix postfix/mailname string mail.example.com" | debconf-set-selections && \
    echo "postfix postfix/main_mailer_type string 'Internet Site'" | debconf-set-selections

RUN apt-get update && apt-get install -y \
    openssh-server \
    postfix \
    dovecot-core \
    dovecot-imapd \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up ssh - create a user with limited access
RUN mkdir /var/run/sshd
RUN useradd -m -s /bin/bash crawler && \
    echo 'crawler:password' | chpasswd && \
    usermod -aG sudo crawler

# Permit root login via SSH
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# allow password auth (fine for local testing)
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# SSH port
EXPOSE 22

# Start SSH service
# CMD ["/usr/sbin/sshd", "-D"]

COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
