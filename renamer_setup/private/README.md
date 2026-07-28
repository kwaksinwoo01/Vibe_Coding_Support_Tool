# Private correspondent build input

Place the private distribution list at:

```text
renamer_setup\private\correspondent.txt
```

Save it as UTF-8 with BOM and enter one correspondent keyword per line. Blank
lines and lines starting with `#` are ignored. The actual file is excluded from
Git and must never be committed.

When the text used for matching must differ from the filename brand, use:

```text
search term | alternate search term => Filename Brand
```

`scripts\build.ps1` automatically embeds this file when it exists. You can also
select another private file with `-CorrespondentFile`. The installer copies the
embedded list only when the installed `config\correspondent.txt` does not exist;
an upgrade preserves the user's existing file.
