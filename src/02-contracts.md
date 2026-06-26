# Contracts

\epigraph{Consensus facit legem. Consent makes the law. A contract is a law between the parties, which can acquire force only by consent.
}{John Bouvier, A Law Dictionary (1856)}

Conceptually, a transaction is a Ricardian contract [@Grigg2004]: plain-text legal prose interspersed with machine-parseable instructions that can refer to participants and attachments. This self-contained format echoes the real life expectation that a contract is its own manifest, and ensures transactions can be cryptographically locked as triple-entry bookkeeping records [@Grigg2005], without sacrificing machine- or human-readability.

The contracts then get normalized, hashed, and enveloped in JSON before signing and sharing. This ensures they can be enriched with metadata such as references (see References), shared incrementally (see Gossip), and signed using existing cryptocurrency hardware if desired.


## Contract Format

Apps MUST support reading, rendering, and sharing contracts in their canonical plain-text format, MUST NOT alter contracts unless they are being redlined (see Redlines), and SHOULD NOT gossip contracts that include pre- or post-processing directives like YAML frontmatter, template variables, or macro substitutions that get substituted on the fly. These specifications offer a templating syntax (see Templates), but assume template recipients will only ever use the reserved signer variable---and use it automatically before display or signing, at that. This ensures the signed byte stream and its rendered form remain unequivocal:

1. Immutability is required because a contract's exact bytes get hashed when signing (see Signatures). Two contracts that render identically but diverge by even one byte produce different hashes and cause signature verification to fail. Avoiding unneeded edits eliminates accidental byte drift across editors and operating systems.

2. Pre- or post-processing are strongly discouraged in contracts because they can break the expectation that "what you see is what you sign." Participants may end up signing identical bytes (`{{amount}}`) with different renderings (`$1,500` vs `1,500 CAD`), for instance. Excluding such directives leaves no room for interpretation.

Apps MAY use plain-text rendering engines like Markdown for display, and MUST declare the contract’s content type in the envelope (see Envelopes) to prevent auto-detection errors and ensure consistent rendering across apps.

_Pandoc_ is highly recommended for display. Its default Markdown flavor enables a plethora of useful features such as tables, footnotes, BibTex citations, and definition lists. It exports cleanly to PDF and other print-ready formats, with style and layout customizations available through a separate metadata file.

Apps MAY provide rich-text editing of contracts, but MUST normalize contracts to plain text for interoperability (see Normalization).

Apps MAY treat the plain-text contract as a simple manifest, with instructions used to attach legal prose, trading directives, binary assets, and other files, in any format. This enables industries to implement domain-specific workflows as they see fit atop this transaction infrastructure, and reap its compelling cost (see Consolidations) and enforceability (see Forensics) benefits. Examples include cross-border transfers and remittances, vendor invoice factoring, forex trading, and cross-blockchain asset bridging.


## Redlines

Apps MUST support redlining transactions by simply editing their contract.

Apps MUST NOT allow redlining finalized transactions, but SHOULD allow creating new transactions based on finalized transactions as a UI convenience ("Create a Copy" button or equivalent).

Apps MUST amend the envelope of any contract they redline (see Envelopes):

1. Process the references the contract came enveloped with normally.

2. Discard the signatures enveloped with the contract's original version, since changing the contract's bytes will make them all invalid.

3. Reprocess other envelope fields as called for (new ID, potentially different type and title, and other changes that may apply).

Redlines mean that diverging versions of a contract might be circulating at the same time, each with different edits. This can become chaotic with more than a few participants, so apps SHOULD cluster contract versions (e.g. the original as the root, then each redline as a branch, each with its own thread) to keep the UI intelligible when multiple versions of the same contract are competing for finalization.

Ledger controllers MAY add or remove transaction participants when redlining, at that, so there isn't even a guarantee that the participants stay the same, and participants that don't yet realize they've been dropped might revive old versions of a contract in the same way that old email or forum threads do.

Apps MUST automatically redline their own rotated ledger keys (and only those) from their old value to their new value before gossiping transactions that are not yet finalized.


## Normalization

The takeaway for non-technical readers: Normalization is rendered necessary for good interoperability.

Normalization is an automated redline (see Redlines) so should be avoided in spirit, but is needed for three reasons in practice.

The first reason is the unspeakable mess of non-unicode based string processing in the software industry. Things have improved during this author's career, but anyone who has wrestled with guessing the disparate encodings of data stored in database columns intended for a mismatched encoding so as to convert that gunk will know to not touch non-unicode data with a barge pole---and to demand UTF-8 at that, because sane languages only support that option anyway.

The next reason is the soul-crushing exercise of reformatting text copied and and pasted from one application to another. You'd think mangled line endings belong to a bygone era, but they aren't yet as of writing in 2026. Perhaps the flood of vibe-coded apps will force the industry to get its act together.

The final reason is the haunting desolation that fills users when two strings produce different cryptographic hashes despite looking the same. This author's opinion on the topic is that apps MUST NOT edit a contract unless the end-user actually intends to redline it. Still, Murphy's Law dictates that a user will stare down this abyss one fateful day, so stripping invisible characters that sneak in when copying and pasting is the least apps can do.

With this in mind, apps MUST normalize contracts and other text-based payloads before hashing them (see Signatures) or adding them to the transaction envelope (see Envelopes), by doing the following:

1. Ensure the normalization input is valid UTF-8, and flag it for user review if not. Apps MUST NOT attempt to "fix" invalid UTF-8 input automatically, and MUST NOT accept to hash invalid UTF-8---let end-users review the sewage and decide what to do.

2. Normalize text sequences to Unicode Normalization Form Composed (NFC).

3. Normalize CRLF (`\x0D\x0A`), CR (`\x0D`), and the Unicode line (Zl) and paragraph (Zp) general categories to LF (`\x0A`).

4. Strip characters in the Unicode "Other, Format" (Cf) general category except bidirectional **isolate** controls---LRI (`\x2066`), RLI (`\x2067`), FSI (`\x2068`), and PDI (`\x2069`). This removes zero-width characters, general bi-directional text controls, language tags, and other invisible junk like the Byte Order Mark (BOM) needed only for UTF-16 and 32 or syllable hyphens (SHY) that users inadvertently add when using the clipboard, while keeping the isolate controls needed to ensure right-to-left and left-to-right text play well when mixed. (Older bidirectional controls are deprecated.)

Apps MAY, of course, use any charset, line-ending, normalization form, and so forth internally, so long as the final output is normalized UTF-8 plain text.

As noted earlier, apps MAY provide rich-text editing of contracts, but MUST normalize them to plain text. Vendors that offer rich-text editing SHOULD look into _Pandoc_. It can convert formats such as HTML or Microsoft Word to plain Markdown out of the box using battle-tested pipelines.

Apps SHOULD NOT normalize gratuitously beyond this. Stripping whitespace from line endings will trash Markdown line breaks. Adding a trailing LF at the end of a file makes no sense for minified JSON. All normalization operations are automated redlines. It may seem smart today---but could it eventually change a contract's semantics and blow up in an end-user's face? If it might, then the right thing to do is to simply _not_ do it.


## Templates

Templates, as the name implies, enable creating contracts based on a template. These are useful in a wide range of situations, including but not limited to:

- A checkout system like an NFC- or QR code-based point of sale device, where a merchant pre-fills a contract using a buyer's ledger key before inviting them to sign it (a payload is typically too large for a QR code or an NFC tap, so those usually get used to bootstrap a saner channel; see Bootstrap Handles).

- A self-checkout system like a buy button, where a buyer must add their ledger key to a contract before signing.

- A recurring contract, where the merchant and the buyer agree on an invoice template to be filled using a trigger each month (see Executable Actions).

- An individualized invitation sent to each community member by an organizer ahead of a vote (see Routing Actions, Optional Signers, and Communities).

Apps SHOULD support the logic-less Mustache templating language in contracts, and MUST support the reserved `{{_}}` Mustache-like template variable if they opt to not support Mustache.

Mustache is a unique templating engine for two reasons: it is widely available, and it offers no if statements, else clauses, or for loops---only conditional blocks and iterators based on pre-defined template data.

Mustache offers a `lambda` feature that violates its own "logicless" security boundary, however, and a few other pitfalls that warrant attention. Apps MUST:

1. Disable HTML escaping for all variable interpolations.

2. Make rendering fail with an error when a key is undefined or `null`.

3. Normalize templates before using Mustache (see Normalization).

4. Forbid lambda functions, partial tags, and delimiter changes by default, since they introduce security and interoperability problems.

Apps MAY enable lambda functions, partial tags, and delimiter changes so ledger controllers can use them internally, but MUST evaluate templates that use those locally before gossiping.

Apps MUST reserve the `_` template variable (so it looks like `{{_}}`) to mean the signer's ledger key in `did:key` format. Combining this with a `Customer` definition (see Instructions) enables gossiping a drafted contract, and letting the customer set the relevant key as a redline before signing (see Redlines).

Apps MUST automatically detect and replace the `_` template variable with the ledger key, when displaying or signing a contract that does not include that ledger as a required signer already (see Finalization). This makes templates transparent to customers, while allowing merchants to create and gossip them normally.

There is no syntax to pass a data mapping to another app, since any scenario that might hypothetically need it is better off using a draft contract with a `{{_}}` for the signer's key, or a trigger in a master service agreement that makes the variables explicit for use in future transactions.

Other template data will invariably get evaluated internally by a trigger that takes a template attached to a contract and injects preconfigured data set at signing time, or by mailing list processing tools (if any) during an outreach campaign that consume `csv` data or similar.


## `.p2pledger` Files

`.p2pledger` files are intended for self-checkout scenarios like buy buttons on websites or sales proposals. Conceptually, these all revolve around downloading and opening a transaction, and sending a signed copy back to the merchant.

`.p2pledger` files are _unencrypted_ so anyone can preview them, so should not contain sensitive information.

Opening the `.p2pledger` file might be a customer's very first interaction with that file's originator, so the file packs everything needed to close the deal: the transaction envelope (see Envelopes), a signature promise (see Promises), a bootstrap handle with at least one return address (see Bootstrap Handles), and the contract itself---typically one with the `_` template variable to automate redlining the customer's ledger key (see Templates and Redlines). The customer signs the contract, gossips it back, and gets their finalized copy in return.

A transaction file's layout is that of a Gossip payload (see Gossip and Payload Format), without the usual encryption so anyone can open it. It MUST be a flat CBOR map (RFC 8949), without a self-describing tag, containing the contract and its envelope, both indexed by their Content Identifiers (see Identifiers). The envelope MUST be pre-signed by at least one counterparty (typically a promise by the originator), and these pre-signers MUST all include a bootstrap handle with at least one non-local return address (see Address Proofs). The contract MAY contain the `_` template variable.

Apps MUST compress this CBOR map using raw DEFLATE (RFC 1951, without the ZLIB header or GZIP wrapper), MUST prepend that compressed payload with the ASCII characters `P2PL` (`0x50 0x32 0x50 0x4C`) to allow for file type scanning, and MUST write it, unencrypted, inside a `.p2pledger` file.

Desktop and laptop apps MUST register themselves as `.p2pledger` file handlers, with the `application/p2pledger` MIME type, and a Uniform Type Identifier (UTI) of `local.p2pledger` conforming to `public.data` on Apple platforms.

The flow outlined above is rather different from the usual web-based buy button that encodes an amount and a currency, requires you to tick a checkbox to agree to terms that even courts acknowledge no one reads, and sends you off to you to a payment processor. It instead presents you with an actual contract, with the terms that you're agreeing to included, and requires that you send your signed copy back. That makes what you agree to much more deliberate and unequivocal.
