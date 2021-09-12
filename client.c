#include <ctype.h>
#include <pwd.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <openssl/evp.h>
#include <sys/stat.h>

#define USERNAME_LEN 8
#define MAX_STR_LEN 300
#define CURL_INIT_ERROR 2
#define CURL_UPLOAD_ERROR 26

int is_valid_name(char *name);
char **query_filenames(char *owner, char *course, char *assignment);
char **parse_filenames(char *response);
int get_file_count(char *response);
int request_scores(char *owner, char *username, char *course, char *assignment,
                   char **filenames);
char *create_key(char *username);
char *get_date();


int main(int argc, char *argv[]) {
    char *course = argc >= 2 ? argv[1] : NULL;
    char *assignment = argc >= 3 ? argv[2] : NULL;
    char *owner = NULL;
    char *username = NULL;
    char **filenames = NULL;
    struct stat file_info;
    int status = 0;

    stat(argv[0], &file_info);
    owner = calloc(USERNAME_LEN + 1, sizeof(char));
    strcpy(owner, getpwuid(file_info.st_uid)->pw_name);

    if (!course) {
        printf("[%s] Course number required\n", argv[0]);
        return -1;
    } else if (!is_valid_name(course)) {
        printf("[%s] Invalid course: %s\n", argv[0], course);
        return -1;
    }

    if (assignment) {
        if (!is_valid_name(assignment)) {
            printf("[%s] Invalid assignment: %s\n", argv[0], assignment);
            return -1;
        }
        filenames = query_filenames(owner, course, assignment);
        if (!filenames) {
            printf("[%s] Unable to query file names\n", argv[0]);
            return -1;
        }
    }

    username = calloc(USERNAME_LEN + 1, sizeof(char));
    strcpy(username, getpwuid(getuid())->pw_name);
    status = request_scores(owner, username, course, assignment, filenames);

    if (status) {
        if (status == CURL_INIT_ERROR) {
            printf("[%s] Unable to initialize client\n", argv[0]);
        } else if (status == CURL_UPLOAD_ERROR) {
            printf("[%s] Unable to upload file(s):", argv[0]);
            for (int i = 0; filenames[i]; ++i) {
                printf(" %s", filenames[i]);
            }
            printf("\n");
        } else {
            printf("[%s] Unable to connect to server\n", argv[0]);
        }
    }

    if (filenames) {
        for (int i = 0; filenames[i]; ++i) {
            if (filenames[i]) {
                free(filenames[i]);
            }
        }
        free(filenames);
    }
    if (status) {
        return -1;
    }

    return 0;
}


int is_valid_name(char *name) {
    for (int i = 0; name[i]; ++i) {
        if (!isalnum(name[i]) && name[i] != '_') {
            return 0;
        }
    }

    return 1;
}


char **query_filenames(char *owner, char *course, char *assignment) {
    char **filenames = NULL;
    char *response = calloc(MAX_STR_LEN, sizeof(char));
    char cmd[MAX_STR_LEN] = "";
    FILE *fp = NULL;

    sprintf(cmd, "/bin/curl -s %s:%s/%s/%s/%s/", DOMAIN, PORT,
            owner, course, assignment);

    fp = popen(cmd, "r");
    fgets(response, MAX_STR_LEN, fp);
    pclose(fp);

    if (!*response) {
        return NULL;
    }

    filenames = parse_filenames(response);

    free(response);
    return filenames;
}


char **parse_filenames(char *response) {
    int n_files = get_file_count(response);
    char **filenames = calloc(n_files + 1, sizeof(char *));
    char *token = NULL;

    for (int i = 0; i < n_files; ++i) {
        token = strtok(response, " \n");
        filenames[i] = calloc(strlen(token) + 1, sizeof(char));
        strcpy(filenames[i], token);
        if (i == 0) {
            response = NULL;
        }
    }

    return filenames;
}


int get_file_count(char *response) {
    int count = 0;

    do {
        response = strchr(response + sizeof(char), ' ');
        ++count;
    } while (response);

    return count;
}


int request_scores(char *owner, char *username, char *course, char *assignment,
                   char **filenames) {
    char *key = create_key(username);
    char cmd[MAX_STR_LEN] = "";
    char file_arg[MAX_STR_LEN] = "";
    char response[MAX_STR_LEN] = "";
    FILE *fp = NULL;

    sprintf(cmd, "/bin/curl -s %s:%s/%s/%s/%s/%s/", DOMAIN, PORT,
            owner, username, key, course);

    if (assignment) {
        strcat(cmd, strcat(assignment, "/"));
        if (filenames) {
            for (int i = 0; filenames[i]; ++i) {
                sprintf(file_arg, " -F %1$s=@%1$s", filenames[i]);
                strcat(cmd, file_arg);
            }
        }
    }

    fp = popen(cmd, "r");
    while (!feof(fp)) {
        fgets(response, MAX_STR_LEN, fp);
        if (*response) {
            printf("%s", response);
            response[0] = '\0';
        }
    }

    free(key);
    return WEXITSTATUS(pclose(fp));
}


char *create_key(char *username) {
    char *key = NULL;
    char *date = get_date();
    unsigned int md_len = 0;
    unsigned char *md_value = calloc(EVP_MAX_MD_SIZE, sizeof(char));

    EVP_MD_CTX *mdctx = EVP_MD_CTX_create();
    EVP_DigestInit_ex(mdctx, EVP_sha512(), NULL);
    EVP_DigestUpdate(mdctx, username, strlen(username));
    EVP_DigestUpdate(mdctx, date, strlen(date));
    EVP_DigestUpdate(mdctx, KEY, strlen(KEY));
    EVP_DigestFinal_ex(mdctx, md_value, &md_len);
    EVP_MD_CTX_destroy(mdctx);
    EVP_cleanup();

    key = calloc(md_len, sizeof(char) * 2 + 1);
    for (int i = 0; i < md_len; ++i) {
        sprintf(key + (i * sizeof(char) * 2), "%02x", md_value[i]);
    }

    free(date);
    free(md_value);
    return key;
}


char *get_date() {
    time_t now = time(NULL);
    struct tm *time_info = localtime(&now);
    int date_len = 11;  // "YYYY/MM/DD\0"
    char *date = calloc(date_len, sizeof(char));

    sprintf(date, "%04u/%02u/%02u", time_info->tm_year + 1900,
            time_info->tm_mon + 1, time_info->tm_mday);

    return date;
}
