#!/bin/bash

printf "::: file_access_manager.access\n\n## Command Line\n\n\u0060\u0060\u0060sh\n$(manage-access -h)\n\u0060\u0060\u0060\n\n### pending\n\n\u0060\u0060\u0060sh\n$(manage-access pending -h)\n\u0060\u0060\u0060\n\n### check\n\n\u0060\u0060\u0060sh\n$(manage-access check -h)\n\u0060\u0060\u0060" > docs_source/functions/Access.md
printf "::: file_access_manager.locations\n\n## Command Line\n\n\u0060\u0060\u0060sh\n$(manage-access locations -h)\n\u0060\u0060\u0060" > docs_source/functions/Locations.md
printf "::: file_access_manager.project\n\n## Command Line\n\n### init\n\n\u0060\u0060\u0060sh\n$(manage-access init -h)\n\u0060\u0060\u0060\n\n### config\n\n\u0060\u0060\u0060sh\n$(manage-access config -h)\n\u0060\u0060\u0060" > docs_source/functions/Projects.md