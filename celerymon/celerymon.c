#include <stdio.h>
#include <unistd.h>

int main() {
    int retval = 0;
    setuid(0);
    /* system("/home/davorian/Code/celerymon/celerymon.sh"); */
    retval = execl("/tmp/celerymon.sh", "celerymon.sh", NULL);
    if (retval != 0) {
        fprintf(stderr, "Error occurred attempting to invoke script: %d\n", retval);
        return retval;
    }
    return 0;
}
