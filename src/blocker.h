/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
typedef struct BbEngine BbEngine;
BbEngine *bb_engine_load(const char *, const char *);
void bb_engine_free(BbEngine *);
void bb_string_free(char *);
int bb_check(const BbEngine *, const char *, const char *, const char *, const char *, char **);
char *bb_cosmetics(const BbEngine *, const char *);
char *bb_generic(const BbEngine *, const char *, const char *, const char *);
