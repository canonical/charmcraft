# Security policy

## Charmcraft and charms

Charmcraft is a tool to create and publish charms. A component of the [Juju]
ecosystem, a charm is a piece of software that orchestrates and manages software
services, and without regular maintenance and updates it can become vulnerable.

A charm's author or maintainer is the sole party responsible for its security. Charm
authors should be diligent and keep the software inside their charms up-to-date with the
latest releases, security patches, and security measures.

Any vulnerabilities found in a charm should be reported to the charm's author or
maintainer.

## Build isolation

In typical operation, Charmcraft makes use of tools like [LXD] and [Multipass] to create
isolated build environments. Charmcraft itself provides no extra security, relying on
these tools to provide secure sandboxing. The security of these build environments
are the responsibility of these tools and should be reported to their respective
project maintainers.

Additionally, [destructive] builds are designed to give full access to the running host
and are not isolated in any way.

## Release cycle

Canonical tracks and responds to vulnerabilities in the latest patch of every
[current major release] of Charmcraft. For a list of supported bases, see the
[base] documentation.

### Supported bases

Bases are tied to Ubuntu LTS releases. For example, the `ubuntu@24.04` base uses Ubuntu
24.04 LTS as its build and runtime environment. This means that Charmcraft's support
of bases aligns with the [Ubuntu LTS release cycle].

The most recent major release of Charmcraft will always support bases still in their
regular maintenance lifecycle. When a major release of Charmcraft drops support for a
base, the previous major release remains supported until the dropped base reaches the
end of its extended support lifecycle.

## Reporting a vulnerability

To report a security issue, file a [Private Security Report] with a description of the
issue, the steps you took to create the issue, affected versions, and, if known,
mitigations for the issue.

The [Ubuntu Security disclosure and embargo policy] contains more information about
what you can expect when you contact us and what we expect from you.

[current major release]: https://documentation.ubuntu.com/charmcraft/stable/release-notes/#current-releases
[base]: https://documentation.ubuntu.com/charmcraft/stable/reference/platforms/#base
[destructive]: https://documentation.ubuntu.com/charmcraft/stable/reference/commands/pack/
[Juju]: https://documentation.ubuntu.com/juju
[Private Security Report]: https://github.com/canonical/charmcraft/security/advisories/new
[LXD]: https://canonical.com/lxd
[Multipass]: https://canonical.com/multipass
[Ubuntu Security disclosure and embargo policy]: https://ubuntu.com/security/disclosure-policy
[Ubuntu LTS release cycle]: https://ubuntu.com/about/release-cycle
