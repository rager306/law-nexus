---
type: cli
actors:
  - operator
entryPoints:
  - cli: law-nexus-inspect health
  - cli: law-nexus-inspect inspect <path>
  - cli: law-nexus-inspect replay <seed-edition> <target-edition>
  - cli: law-nexus-inspect subordinates <resolution|order> <path>
---

# Terminal

The command line of `law-nexus-inspect`: one binary, four subcommands. Every
invocation prints one JSON report or one typed failure record and exits;
there is no session and nothing is kept between runs.
