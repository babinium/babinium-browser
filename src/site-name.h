/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <glib.h>

/* Return the identifying label of the registrable domain for display. */
char *favorite_site_name(const char *uri);
gboolean favorite_title_is_address(const char *title,const char *uri);
