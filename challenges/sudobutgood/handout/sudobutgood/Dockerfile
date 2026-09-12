FROM python:3.14.4-slim-trixie AS chall

RUN apt-get update && apt-get install -y openssh-server vim

# Defang setuid binaries
RUN find / -xdev -perm /4000 -type f -exec chmod a-s {} \; ; true

# Add a user for ssh
RUN <<EOF
    adduser --disabled-password --comment "" ctf
    echo 'ctf:hunter2' | chpasswd
EOF

# Add a user for setuid
RUN adduser --system --group --no-create-home --disabled-password --comment "" admin

COPY --chown=admin:admin flag /
RUN chmod 400 /flag

WORKDIR /app
COPY src/sudobutgood sudobutgood_pass /app/
RUN su -c "ln -s /app/sudobutgood /home/ctf/sudobutgood" ctf

RUN chown admin:admin -R /app/ && chmod 4555 /app/sudobutgood && chmod 400 /app/sudobutgood_pass

# Configure default ssh shell as bash
RUN chsh -s /bin/bash ctf

# Configure sshd
RUN echo 'AllowUsers ctf' >> /etc/ssh/sshd_config
RUN ssh-keygen -A

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
