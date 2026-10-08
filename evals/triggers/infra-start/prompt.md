---
description: An infrastructure request spanning clouds and environments reaches the infra entry point.
tags: [trigger, infra]
max_turns: 10
allowed_tools: [Skill, Read, Glob, Grep, AskUserQuestion]
---

We deploy to Kubernetes on AWS today and need the same platform on Azure, with separate test, staging and production environments managed with Terraform and Argo CD. Where do we start?
