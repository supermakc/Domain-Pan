#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define SCRIPT_NAME "celerymon.sh"

int main(int argc, char **argv) {
    int retval = 0;
    char fullpath[1024];

    strcpy(fullpath, argv[1]);
    strcat(fullpath, SCRIPT_NAME);

    setuid(0);
    if (argc < 2) {
        fprintf(stderr, "Usage: celermon <path-of-celerymon.sh> [worker-prefix]\n");
        fprintf(stderr, "   Path note: the trailing slash must be included.");
        return 1;
    }

    if (argc > 2) {
        retval = execl(fullpath, SCRIPT_NAME, argv[2], NULL);
    }
    else {
        retval = execl(fullpath, SCRIPT_NAME, NULL);
    }

    if (retval != 0) {
        fprintf(stderr, "Error occurred attempting to invoke script: %d\n", retval);
        return retval;
    }

    return 0;
}
