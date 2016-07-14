# Lektor Blog Posts Plugin

A [Lektor](https://www.getlektor.com/) plugin customized for administering A. Jesse Jiryu Davis's personal website [emptysqua.re](https://emptysqua.re).

## Commands

Installing this plugin creates a `blog` command-line program. For instructions:

```
blog --help
```

## Shell Auto-Completion

Something like this in ZSH configures auto-completion in the shell:

```
compctl -k "(list new open preview protect publish visit reveal path)" \
    -x 'c[-1,publish][-1,open][-1,preview][-1,visit][-1,reveal]' -/ -W content/blog \
    - 'c[-1,list]' -k "(posts pages drafts tags categories)"  \
    - 'c[-1,new]' -k "(draft)"  \
    - 'c[-2,draft]' -/ \
    -- blog
```
