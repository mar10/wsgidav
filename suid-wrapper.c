#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <cap-ng.h>
#include <errno.h>
#include <pwd.h>

int
main(int argc, char *argv[], char *envp[])
{
	int ret;
	struct passwd *pwd = NULL;
	uid_t uid;
	gid_t gid;

	if (argc <= 2) {
		fprintf(stderr, "usage: %s user cmd argv [argv]\n", argv[0]);
		return EXIT_FAILURE;
	}

	errno = 0;
	if ((pwd = getpwnam(argv[1])) == NULL) {
		if (errno != 0) perror("getpanam");
		else fprintf(stderr, "getpwnam: can not find user %s\n", argv[1]);
		return EXIT_FAILURE;
	}

	uid = pwd->pw_uid;
	gid = pwd->pw_gid;

	if (uid == 0) {
		fprintf(stderr, "can not run as root (uid = 0)\n");
		return EXIT_FAILURE;
	}

	capng_clear(CAPNG_SELECT_BOTH);

	ret = capng_updatev(CAPNG_ADD,
		CAPNG_EFFECTIVE | CAPNG_PERMITTED | CAPNG_INHERITABLE | CAPNG_AMBIENT,
		CAP_SETUID, CAP_SETGID, -1);
	if (ret < 0) {
		fprintf(stderr, "capng_updatev() returns %d\n", ret);
		return EXIT_FAILURE;
	}

	ret = capng_change_id(uid, gid, CAPNG_INIT_SUPP_GRP);
	if (ret < 0) {
		fprintf(stderr, "capng_change_id() returns %d\n", ret);
		return EXIT_FAILURE;
	}

	errno = 0;
	if (execvpe(argv[2], &argv[2], envp) < 0) {
		perror("execvpe");
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}
