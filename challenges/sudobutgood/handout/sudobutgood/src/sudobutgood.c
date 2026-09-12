#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

void get_hash(const char *input, char *hash_out) {
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        perror("pipe");
        exit(1);
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        exit(1);
    }

    if (pid == 0) {
        // Child process
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO); 
        close(pipefd[1]);

        char *args[] = {
            "/bin/sh",
            "-c",
            "printf \"%s\" \"$1\" | /usr/bin/sha256sum",
            "sh",
            (char *)input,
            NULL
        };

        execve(args[0], args, NULL);
        perror("execve");
        exit(1);
    } else {
        // Parent process
        close(pipefd[1]);
        int num_read = read(pipefd[0], hash_out, 64);
        if (num_read != 64) {
            fprintf(stderr, "Failed to hash password.\n");
            exit(1);
        }
        wait(NULL);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <command>\n", argv[0]);
        return 1;
    }

    FILE *f = fopen("/app/sudobutgood_pass", "r");
    if (!f) {
        perror("Error reading /app/sudobutgood_pass");
        return 1;
    }
    
    char secret_pass[256];
    if (!fgets(secret_pass, sizeof(secret_pass), f)) {
        fprintf(stderr, "Failed to read password.\n");
        return 1;
    }
    fclose(f);
    secret_pass[strcspn(secret_pass, "\n")] = 0;

    char secret_hash[65] = {0};
    get_hash(secret_pass, secret_hash);

    printf("[sudobutgood] enter password: ");
    char user_pass[256];
    if (!fgets(user_pass, sizeof(user_pass), stdin)) {
        return 1;
    }
    user_pass[strcspn(user_pass, "\n")] = 0;

    char user_hash[65] = {0};
    get_hash(user_pass, user_hash);

    if (strncmp(secret_hash, user_hash, 64) == 0) {
        setresuid(geteuid(), geteuid(), geteuid());
        system(argv[1]);
    } else {
        printf("sudobutgood: nah that's not it\n");
    }

    return 0;
}
