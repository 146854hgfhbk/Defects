# Perl environment guide

**Cases: 100**  
**Guide scope: native Perl 5.24/5.36 + cpanm**

## Versions

Perl cases record a container image and digest in `case.json`:

```json
"environment": {
  "container": {
    "image": "perl:5.36",
    "digest": "sha256:..."
  },
  "network": "disabled"
}
```

Observed images:

| Image | Cases |
|---|---:|
| `perl:5.36` | 44 |
| `perl:5.24` | 22 |
| `perl-defects4j/runtime-test-simple-rc212:local` | 19 |
| `perl-defects4j/runtime-http-message-rc213:local` | 5 |
| `perl-defects4j/runtime-extutils-makemaker-rc212:local` | 5 |
| `perl-defects4j/runtime-path-tiny-rc212:local` | 5 |

Use the image/digest from the case, not a global Perl.

## Install native Perl

`perlbrew` is the cleanest way to get 5.24/5.36:

```bash
curl -L https://install.perlbrew.pl | bash
source "$HOME/perl5/perlbrew/etc/bashrc"
perlbrew install perl-5.36.0
perlbrew switch perl-5.36.0
perl -v
cpanm --version
```

For 5.24 use `perlbrew install perl-5.24.4`.

## Dependencies

```bash
cpanm --installdeps .
# or, if the case ships a cpanfile:
cpanm --installdeps --with-develop .
```

Old CPAN modules may no longer resolve from a live mirror. Prefer the case's container image or a prepared CPAN cache.

## Build and test

The case JSON declares commands:

```json
"commands": {
  "build": "perl Makefile.PL && make",
  "trigger_test": "prove -Ilib -It/lib t/Liblist_Kid.t",
  "full_test": "make test"
}
```

Run the **trigger test**, not the full suite, for the differential:

```bash
perl Makefile.PL
make
prove -Ilib -It/lib t/<trigger>.t
```

## Container option

```bash
docker run --rm -it \
  -v "$PWD:/work" -w /work \
  perl:5.36@sha256:<digest> \
  bash -lc 'perl Makefile.PL && make && prove -Ilib -It/lib t/<trigger>.t'
```

## Important

Some Perl cases have audit fields such as `license_evidence: BLOCKED` or `reproducibility_status: BLOCKED`. Check `case.json.status.audit` before claiming full reproducibility. Do not distribute third-party CPAN bundles without a license review.
