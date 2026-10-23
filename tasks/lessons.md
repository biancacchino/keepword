# Lessons

## Describe keepword on its own terms

Never name or compare against other people's projects in repo files, commits, or PRs.
This repo is public and is my work.
Before every commit, grep the diff for outside project names.

## Check for non-ASCII with perl, not grep

Escapes I write (backslash-u plus a code point) can reach the file as the real character, from Write, Bash heredocs, or any tool.
macOS BSD grep does not catch it, even with `LC_ALL=C`.
Before staging, run: `perl -ne 'print "$ARGV:$.: $_" if /[^\x00-\x7f]/; close ARGV if eof' $(git ls-files '*.py' '*.toml')`.
