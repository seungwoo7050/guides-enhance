#ifndef COMMAND_PIPELINE_H
#define COMMAND_PIPELINE_H

/* [Implementation 1] Public two-command execution API */
int run_pipeline(
    char *const left_argv[],
    char *const right_argv[],
    int *out_status
);

#endif
