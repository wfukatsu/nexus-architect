---
description: A database migration request that spans two engines reaches the migration router.
tags: [trigger]
plugins: ["../../.."]
max_turns: 10
allowed_tools: [Skill, Read, Glob, Grep, AskUserQuestion]
---

We run two legacy systems, one on Oracle and one on MySQL, both with stored procedures and triggers. We need to move them to ScalarDB. How do we start?
