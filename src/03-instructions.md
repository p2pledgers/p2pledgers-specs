# Instructions

\epigraph{It is the world of words that creates the world of things.
}{Jacques Lacan, Écrits (1966)}

Instructions are subject/object pairs that allow defining subjects or assigning actions and directives to them.

Plain text contract lines that start with an at-bang (`@!`) mark the start of instructions. Everything after the at-bang until the end of the line is the instruction.

This section glosses over details to stay accessible for non-technical readers. Vendors will find the minutia in Parsing, Envelopes, and Triggers.


## Basic Syntax

An instruction's subject/object pair MUST be separated by a colon (`:`):

    @! Subject: Object

An instruction MAY span multiple lines by indenting continuation lines further than the first one:

    @! Subject: Object
    @!    Continued

Apps MUST treat continuations as a single space at parsing time, including when the continuation comes after unclosed quotes (see Quotes).

An instruction's object MAY have parameters separated by semi-colons (`;`):
 
    @! Subject: Object; param=value

Parameters default to boolean true if the `=value` part is omitted:

    @! Subject: Object; debug

That can of course be abused to add comments anywhere a parameter could start.


### Localization

Instructions were deliberately designed to be language independent, with no English keywords.

Subjects and objects MAY contain any UTF-8 character. This ensures end-users can read and write instructions in their preferred language:

    @! 李明: 王芳 100元     ; Li Ming: Wang Fang 100 CYN (Chinese)

The only hardwired cultural imports are the use of ASCII numerals (1, 2, 3...) in amounts and a few delimiters (`:`, `;`, `=`, etc.) that keyboards typically have because of their use in programming languages.

Apps MAY, of course, use localized numerals and delimiters at display if those are easier to access on local keyboards, but MUST normalize them back to ASCII equivalents internally for interoperability if they do.

    @! राम: सीता रु१००    ; Ram: Sita 100 NPR (Nepali)

Vendors MUST use a custom parsing grammar (see Parsing) to normalize localized numerals and delimiters, so mixing those with their ASCII counterparts doesn't create unwanted redlines. In the previous example, for instance, a naive string replace would affect the `100` in the comment.

Apps MAY similarly localize the dot and underscore (`_`) characters expected by computer parsers in amounts, with the same caveats:

    @! Jean: Marie €1 000,00   ; John: Mary 1_000.00 EUR (French)


### Quotes

Instructions MAY have single or double quotes _inside_ their parts. These are literals with no special meaning:

    @! Subject 'with "quotes: Object 'with "quotes

Instructions MAY also wrap their parts inside single or double quote delimiters with VB-style quote escaping:

    @! "Subject 'with ""quotes": 'Object ''with "quotes'

Such quote delimiters are seldom needed. They help resolve the rare ambiguities when parsing instructions with delimiters in them (see Parsing).


### Indentations

Instruction lines MAY have leading spaces and tabs before their at-bang:

        @! Instruction: with leading spaces before it

This enables putting instructions inside pre-formatted Markdown blocks.

Indentation is significant only when it changes from an instruction line to the next. Apps MUST treat such indentation changes as new blocks (see Parsing).


## Definitions

Definition instructions bind their subject to:

1. An identity, when the object starts with a public key in `did:key` format:

        @! John: did:key:z6MkCMyGw...

2. An attachment, when the object starts with a content ID prefixed with `cid:`:

        @! Terms.pdf: cid:f1220aba4c...

3. A scalar value in every other case:

        @! JohnAuthorization: zdpu6vTR4...

Identities and attachments MUST use these `did:key:` and `cid:` prefixes so they can be distinguished from scalar values.


### Attachments

Apps MUST make all attachments and signatures passed as files in `cid` format that appear in contracts or envelopes (see Envelopes) available for retrieval by other transaction participants using their CID (see Gossip).


### Bindings

Apps MUST resolve references to definition subjects inside other instructions (see Parsing). This enables writing instructions in plain language:

    @! John: Jane 100 USD

Apps MUST treat subjects as case-sensitive, but SHOULD autodetect case-related errors, and MAY offer to redline them before signing the transaction.


### Reserved Bindings

Apps MUST reserve the dot (`.`, for transaction), asterisk (`*`, for all), dash (`-`, for noop, which is pronounced no-op), and the two angle brackets (`>` and `<`, for route and reference) as bindings. These bind to the transaction, all of the signers (for actions) or recipients (for directives), no-operation, and directives respectively:

- `.` enables setting a title (see Transaction Titles), and self-referencing the contract in authorizations and executable actions (see `did:key` Proofs and Executable Actions).

- `*` is a wildcard shorthand that enables individually assigning an executable action to all of a transaction's signers, or a routing directive to all of its assignees (signers or not).

- `-` enables requiring extra signers without committing them to any specific action (see Noop Actions).

- `>` and `<` enable declaring routing and reference directives respectively (see Routing Directives and Reference Directives).


### Transaction Titles

Apps MUST allow assigning a definition to the reserved transaction subject (`.`). Doing so sets the transaction's optional title (see Envelopes):

    @! .: Groceries at Acme ($27.63)

Apps MAY set a title automatically if it is not set, SHOULD use this title in their signing UI if it is set, and SHOULD pass it on in the appropriate format to signing hardware if it is set (see Signing Hardware)---so users are signing e.g. `Groceries at Acme ($27.63)` instead of a cryptic looking hash.


## Actions

Action instructions commit their subjects to:

1. A double-entry bookkeeping line, when their object starts with an identity:

        @! John: Jane -100 USD

2. An executable, when their object starts with an attachment:

        @! Newspaper: Publish.wasm; post=Propaganda.txt

3. No operation ("Noop"), when their object is a dash (`-`):

        @! John: -

Ledgers MUST sign transactions that assign them an action for that transaction to become finalized (see Finalization).

Ledgers MUST process actions assigned to them once the contract gets finalized, and MUST NOT process actions that are not assigned to them.

Apps MUST allow binding an action to the reserved all (`*`) subject:

    @! *: vote.wasm; poll=.


## Bookkeeping Lines

Double-entry bookkeeping lines, or lines for short, consist in an identifier or a ledger key in `did:key` format, an amount, and a currency unit:

    @! John: Jane 100 USD

Line amounts MAY contain underscores (`_`) in between digits for readability:

    @! John: Acme 4_567.89 USD

Bookkeeping lines use positive and negative amounts to represent credits and debits respectively. This convention loses the hair-splitting ability to book negative credits and debits, which are unimportant for our purposes.


### Amounts

Apps MUST support currencies in decimal format. Currency units in use today all use decimals, and countries with more than one subdivision express amounts as decimal numbers in practice, so decimal are enough for all existing currencies---apps need not support octal or duodecimal or vigesimal units.

Apps MUST support line amounts with _at least_ 9 decimals of precision. That number accommodates all traditional currencies (financial systems usually have 4 digits of precision), 1 BTC = 10^8 satoshis, and 1 ETH = 10^9 Gwei. Vendors SHOULD monitor what the maximum practical precision of currencies with traction is, and adopt if needed. (ERC-20 cryptocurrencies like ETH support 18 decimals under the hood.)

Apps MUST reject line amounts they cannot honor. In plain text for vendors: a transaction graph plagued with integer overflows and float-related rounding errors is not helpful, so reject (malicious?) transactions that create such problems as a pre-flight check, and use arbitrary-precision or integer-based arithmetic for all bookkeeping calculations.


### Currency Units

Apps MUST support standard currency codes (ISO 4217 as of writing), SHOULD let users enter any arbitrary unit, and MUST support unit equivalence clusters (1 USD = $1, see Unit Clusters), if at a basic level for de-duplication purposes. This ensures transactions can co-exist inside ledgers with inconsistent unit semantics.

In principle, this implies that ledgers _could_ refer to different realities as `Dollars`. In practice, gossip and consolidation (see Gossip and Consolidation) solve this by sharing the unit clusters, and disincentivizes jokers by saddling them with unwanted liabilities that they then need to clear up in Disputes (see Disputes). The unit clusters basically ensure that meaning converges locally.


### Currency Formats

Whereas examples in these specs use the accounting convention of putting the account followed the amount and a unit in ISO format (or a custom unit), the reference grammar (see Parsing) supports just about every freeform currency format in use today: with units prefixed, infixed, or suffixed, with or without redundant ISO codes, with or without spaces, or with quoted or unquoted custom units of any length.

    @! John: Jane 100 Chickens
    @! John: Jane 100 19L Buckets of Compost
    @! John: Jane 100 "19L Buckets of Compost"
    @! John: Jane USD $1      ; or $1 USD, EUR 1 €, 1 $ CAD, ...
    @! John: Jane $1          ; or $1, € 1, USD 1, 1EUR, ...
    @! John: Jane $.02        ; .02 USD, also £.02, ...
    @! John: Jane Fr.1        ; 1 CHF, also Rs.1, B/.1, ...
    @! John: Jane €1.-        ; 1.00 EUR, also €1-, 1.-€, ...
    @! John: Jane £1p02       ; 1.02 GBP, 1$02, 1Fr.02, ...

Apps SHOULD take the UI/UX highground and let end-users use natural language in amount inputs instead of forcing them to use "two-box" (Amount | Unit) designs reminiscent of 1990s database entry, and use ledger statistics to guess what an ambiguous unit is (e.g. assume $1 is USD if the ledger is full of USD)---or for that matter, offer to autocomplete units as they get typed.


### Balancing

Bookkeeping instructions MUST balance to zero for every counterparty pair in every currency unit. Put another way, if my ledger has a transaction that says I owe you something, then your ledger has a transaction to the same effect the other way around (or several transactions that do in aggregate). This reflects the exchange of bearer notes that the ledger entries mirror.

Apps SHOULD insert and autocorrect bookkeeping lines to keep them balanced, or better yet provide dedicated UI, so ledger controllers can type what they're spending (minus) or receiving (plus) from their viewpoint and not worry about balancing double-entry bookkeeping lines. Vendors SHOULD NOT try to impose one "correct" sign---some cases are best thought of as paying or now owing, while others are best thought of as receiving or no longer owing, so let users do both and balance the lines for them under the hood.

Apps MUST reject unbalanced transactions as invalid. Apps MAY store unbalanced transactions for drafting purposes, but MUST NOT gossip them (see Gossip).


### Example Transactions

A simple transaction where Jane pays John 100 USD:

    @! Jane: John -100 USD
    @! John: Jane  100 USD

As mentioned earlier, picturing notes being exchanged can make the accounting easier to follow. The first and second lines mean "Jane issues John a 100 USD IOU" and "John accepts Jane's 100 USD IOU" respectively. In ledger terms, the same lines mean that Jane and John book "John owes me 100 USD less" and "Jane owes me 100 USD more" respectively.

Apps SHOULD, it goes without saying, provide UI that translates the accounting lines to plain language from the end-users's viewpoint. Legal shitfuckery might make Send and Receive or Deposit and Withdraw poor word choices, and Credit and Debit might be too esoteric, but simple directional arrows would fit right in---arrows are fine ways to represent edges on a directed IOU graph, and users will naturally associate them with sending and receiving.

A consolidation transaction between John, Jane, and Jack, where each other's debt to the next cancels the other's, illustrates the same point. It's often easier to think of transactions as bearer notes that are being passed around (John takes Jane's note while issuing one to Jack, etc.):

    @! John: Jane  100 USD
    @! John: Jack -100 USD
    @! Jane: Jack  100 USD
    @! Jane: John -100 USD
    @! Jack: John  100 USD
    @! Jack: Jane -100 USD

A transaction where John sells Jane's debt to Jack for 97% of its value, which again is equivalent to a bearer note changing hands, and mirrors what trading government bonds and mortgages looks like (those command a premium marked up or down by the debtor's perceived ability to pay the principal and the interest):

    @! Jane: John -100 USD
    @! Jane: Jack  100 USD
    @! Jack: Jane -100 USD
    @! Jack: John    3 USD
    @! John: Jane  100 USD
    @! John: Jack   -3 USD

A spot gold trade where John sells 1 XUA to Jane, in exchange for 4,567.89 USD paid in full through an intermediary Acme, with the seller John paying a 0.5% commission booked on separate lines to make what's going on easier to follow:

    @! John: Jane     -1    XAU
    @! John: Acme  4_567.89 USD
    @! John: Acme    -22.84 USD
    @! Acme: John -4_567.89 USD
    @! Acme: John     22.84 USD
    @! Acme: Jane  4_567.89 USD
    @! Jane: Acme -4_567.89 USD
    @! Jane: John      1    XAU

A two-step transaction, where John pays Acme to fill an anonymized Anon ledger (which makes Anon creditworthy according to Acme), and then using that to pay Jack with Acme serving as an intermediary:

    @! John: Acme -101 USD
    @! Acme: John  101 USD
    @! Acme: Anon -100 USD
    @! Anon: Acme  100 USD

    @! Anon: Acme -100 USD
    @! Acme: Anon  100 USD
    @! Acme: Jack  -99 USD
    @! Jack: Acme   99 USD


## Executable Actions

Executable actions add Turing-complete scriptability to the transaction graph, by contractually committing participants to execute software as they see fit.

Executable actions MUST reference a file attached to the transaction, called trigger files, or triggers for short, and MAY accept any number of parameters. While trigger files MAY be in written using any programming language and have any format in principle, WebAssembly is _strongly_ recommended.

What triggers do is entirely up to the transaction participants and limited only by what programming languages allow: create new transactions at future dates to implement recurring payments, sign such future transactions, handle canceling them, bridge on- and off-graph activities, and more. The Triggers section has the details.

Apps MUST support _assigning_ triggers, but MAY support _executing_ triggers at their discretion. It is completely optional because:

1. They're a scripting feature intended for power-users first and foremost.

2. End-users that do use triggers will likely want an app that runs triggers from a laptop or server, and a lighter app that stays in sync but ignores triggers on their mobile phone.

3. They add complexity that not all vendors or apps will want, and especially not apps intended to run on mobile devices.

Apps that support executable actions MUST allow individual ledgers to enable and disable executing triggers as they see fit, and in fact SHOULD default to executing triggers being disabled to simplify transaction locking (see Locks).

Because supporting _executing_ triggers is optional, apps MUST warn end-users before letting them sign transactions that assign them executable actions that they cannot honor---because triggers aren't supported or are disabled, or that language isn't supported, or the app can't honor the required capabilities (see Capabilities).

Failing to execute triggers (see Triggers) _is_ a breach of contract, with the usual consequences if not remedied promptly (see Disputes).


### Sandboxing

Vendors will no doubt author triggers to cover common use cases, like recurring transactions, wire transfers, and cryptocurrency transactions, and tech-savvy ledger controllers will no doubt author many more for their own purposes. Such authors are trusted, if only _de facto_, so the security risks tied to running their code is inherent and consummated.

End-users might also latch onto one or more community-driven efforts to market pre-written ones. Vendors MAY, of course, join and perhaps even instigate such bandwagons---all sorts of consolidation, escrow, and voting requirements today depend on incumbents that are ripe for counter-positioning.

For this reason, apps SHOULD support running executables in safe languages only (WebAssembly is the only such option as of writing), SHOULD warn end-users that are signing up to run triggers in any other language (it's on them if they do it anyway), and SHOULD run executables inside some kind of sandbox or virtual machine _only_. Moreover, ledgers SHOULD NOT expose options to easily disable these guards. Heeding these suggestions will help avert the security problems that plagued early internet browsers.


## Noop Actions

Noop actions, or "No-Op", for No Operation, enable adding signing participants, so witnesses and the like can be required to finalize a transaction:

    @! Witness: -


## Decorators

Apps MUST support adding decorators to definitions. Any number of decorators can be added, in any order, after the object definition itself.


### Proofs

Apps MUST support enumerating proof decorators after definitions. Proofs MUST be formatted in between angle brackets (`<` and `>`), with scheme followed by a colon (`:`) separator and a locator:

    @! subject: object <scheme:locator>

Proofs enable adding or removing public keys, addresses, and authorizations to identities, and enable signing attachments.

Proof locators MAY be followed by up to two optional arguments, each separated by a dollar (`$`) sign. One is a date that enables controlling when the proof is valid. The other enables passing arguments during verifications (see Proof Verifications). Their formats are unequivocal, so they MAY be passed in either order, and either or both MAY be omitted:

    @! subject: object <scheme:locator$date$args>

The proof date MUST be in the UTC timezone, and MUST be formatted in ISO 8601 Extended format as calendar dates (`2026-04-10` at midnight) or with a specific time with whole seconds (`2026-04-10T00:00:00Z`). This date means a declaration (or a reinstatement, for a revoked address that gets recovered). If prefixed with a minus (`-`), it means a revocation (see Authentication) instead. Proof dates are inclusive. A dot (`.`) or minus (`-`) without an explicit MAY be used as a shorthand for a reinstatement or revocation from the transaction's date respectively (see Finalization). All proofs MAY be revoked. Address proofs MAY be reinstated, by separating each date with a comma (`,`) to define a sequence of state-change events (in any order).

The other arguments MUST be formatted like a URI query string (RFC 3986). These allow configuring authorizations (see `/sign` authorizations) and address proofs that need to overcome hostile transmission contexts like corporate email firewalls (see Steganography).

Apps MUST NOT needlessly clutter contracts with proofs. The time to share keys and addresses is on first contact, on key rotation, and on address change (see Bootstrap Handles, Key Rotations, and Address Changes).


### `did:key` Proofs

Apps MUST support using public keys in `did:key` format as a proof scheme, or `did:key` proofs for short, and MUST _always_ verify `did:key` proofs during due diligence (see Due Diligence). `did:key` proofs enable:

- A participant to sign a new ledger key using an old key (see Key Rotations and Authentication):

        @! John: did:key:z6MkCMyGw... <JohnOldKey:JohnOldKey.sig>

- A non-signing participant to vet an attachment (or a scalar) without needing to sign the contract (a common requirement in bureaucracies):

        @! Specs.pdf: f1220e1d90... <Engineering:Specs.pdf.sig>

- All participants to attach a `/sign/contract` authorization scoped on `claim` to a ledger in order to grant it arbitral authority over a transaction (see `/sign` Authorizations and Disputes):

        @! AuthorityName: did:key:z6MkFSjsA... <*:.>

- A participant to attach an arbitrary UCAN authorization, for any purpose, and enable other participants to verify its form (see Vouching):

        @! Authorization: zdpu6Xm8h... <John:.>

As the above examples hint at, apps MUST support signatures in `varsig` format and signatures passed as files in `cid` format, MUST allow aliases in `did:key` proof schemes and locators (see Definitions and Parsing), and how apps verify `did:key` proofs exactly (see Signature Verification) depends on the locator and the object.

In the first two examples, the `did:key` proof represents a typical signature. The payload is the object, the signing key is the scheme, and the signature is the locator:

    @! Subject: Payload <SigningKey:Signature>

When the locator is the reserved transaction (`.`) binding and the object is a key in `did:key` format, the signer is granting arbitral authority to that key over the transaction. The payload is a `/sign/contract` authorization gated on `claim` _for_ that ledger key (see `/sign` Authorizations), the scheme MUST be set to the reserved signers (`*`) shorthand to indicate that all participants MUST sign the authorization (including optional signers; see Optional Signers), and the authorizations are added to the envelope so the contract doesn't need redlining when attaching them (see Redlines and Envelopes):

    @! AuthorityName: Key <*:.>

Participants MAY grant arbitral authority to any number of trusted ledgers---or none at all. These authorizations mirror jurisdiction clauses in contracts, and simply make explicit what those do implicitly. Moreover, granting an arbitral authority is a form of _de facto_ vouching---the only salient difference is the vouched ledger doesn't know it's been vouched until the authorization gets used to start a dispute.

When the locator is the reserved transaction (`.`) binding and the object is anything else, the object is an arbitrary UCAN authorization, and the signing key is the scheme as usual:

    @! AttachmentName: UCAN <SigningKey:.>

In the latter case, apps stick with verifying the form, since they have no way of knowing if the substance checks out. Apps MAY support custom authorization types on top of the usual `/sign` ones and verify their substance accordingly (see UCAN Payloads).

`did:key` proofs that had been granted unilaterally MAY be used to revoke keys and authorizations by signing them with a revocation date:

    @! JohnOldKey: did:key:z6MkenSNH... <John:JohnKey.sig$->
    @! Authorization: zdpu6Xm8h... <John:.$->

Arbitral authority grants MAY get revoked by attaching the authorization in a transaction, but the transaction MUST get signed by **all** of the required signers of that signed the instruction that got used to create it. This ensures arbitral authority grants can be revoked if and only if its signers all agree:

    @! AuthorityGrantJohn: zdpu55WNS... <John:.$->
    @! AuthorityGrantJane: zdpuCsWh9... <Jane:.$->
    @! John: -
    @! Jane: -

Revoking keys and authorizations is permanent (see Authorizations). 

Proof dates passed to `did:key` proofs MAY be set in the future, for scheduled key rotations (see Key Rotations), and scheduled authorization revocations:

    @! John: did:key:z6MkCMyGw...
        <John:JohnKey.sig     $-2026-06-01>
    @! JohnNextKey: did:key:z6Mk2WcvT...
        <John:JohnNextKey.sig $ 2026-06-01>

    @! Authorization: zdpu6Xm8h... <John:.> <John:.$-2027-06-01>

As discussed under `/sign` Authorizations, legal deadlines are social. Apps MUST disallow scheduling the revocation of arbitral authority grants this way, with a notice that expired arbitral authority grants would preclude concluding disputes that drag on beyond that.


### Address Proofs

Other types of proofs are collectively called address proofs, because they are Gossip and Trust API endpoints (see Gossip and Trust). These addresses MAY double as authentication proofs for account recovery (see Authentication).

Bootstrap handles automate discovering proximity-based endpoints (see Bootstrap Handles), so don't need to be shared using address proofs. A QR code scan or an NFC tap will typically bootstrap a channel using Bluetooth, the local WiFi, or a public website:

- Bluetooth endpoints MUST use the `ble` scheme, MUST use the payload's size header (see Payload Format) to identify the payload boundaries, and MUST behave like bidirectional file drop-like endpoints (without response codes) that immediately reverse roles to stream return frames.

- LAN-based endpoints like WiFi MUST use the `http` scheme to avoid certificate warnings, and MUST expose the Gossip and Trust API endpoints of the URI/IP channel (with response codes).

Address proofs are intended for non-local endpoints: interactive ones like the URI/IP endpoint, and non-interactive, fire-and-forget ones like email, phone notification, or file-drops on a public web folder. Such endpoints are always OPTIONAL: lacking addresses, transactions advance one step at a time as ledgers interact via proximity-based endpoints. It's not as fast, but it works too.

The Gossip and Trust protocols handle time-outs and rescheduling, so address proof verifications are not needed---an address that yields a signed response is verified _de facto_.

Apps MUST support consuming URI/IP-based Gossip and Trust endpoints declared using the `http` or `https` scheme (payloads are encrypted, so either works):

    @! John: did:key:z6MkCMyGw... <https://api.acme.com>

Apps MUST support pushing fire-and-forget Gossip to non-interactive endpoints declared using the `mailto` scheme:

    @! John: did:key:z6MkCMyGw... <mailto:john@acme.com>

Apps MAY support other address proof schemes and file drop-like endpoints as they see fit. They are innumerable, so here are a few examples:

- Mobile phone notifications, declared using the `tel` scheme and a phone number as the locator (allow optional formatting of phone numbers for human-readability):

        @! John: did:key:z6MkCMyGw... <tel:+1-123-456-7890>

- Cloud-based web folders declared using their domain as a scheme and a unique handle as the locator:

        @! John: did:key:z6MkCMyGw... <drive.google.com:AbCdE...>

- Private messages on social media declared using their URN or their domain as a scheme and a unique handle as the locator (allow optional formatting of phone numbers for human-readability here too):

        @! John: did:key:z6MkCMyGw... <facebook.com:john> <x.com:john>
            <whatsapp:+1-123-456-7890> <tg:john> <matrix:john@acme.com>

Vendor prefixes are undesirable for address proof schemes, since the only thing that matters is verifying the claim by checking that the endpoint works. If the verifier doesn't get an answer, they don't verify the address and don't push to it---simple as that. Plus, APIs tend to be stable to avoid uproar. At worst, an API changes, and Gossip tries another channel.

Apps MAY expose more than one endpoint with the same scheme---having two email addresses is commonplace.

End-users often enter addresses in their preferred communication order, so apps SHOULD monitor which they enter first, SHOULD allow them to reorder them, and SHOULD reflect their preferred ordering when communicating address proofs.

Conversely, apps SHOULD monitor the order they receive address proofs in, and SHOULD factor that when deciding where to send gossip.

Apps MUST NOT share the address proofs of ledgers they don't hold, since these are contact details that ledger controllers might not want to share.

Apps MAY omit any or all of the API endpoints they advertise in address proofs, and SHOULD omit the addresses of non-interactive transports by default. Sharing your email or phone number with random strangers is seldom desirable.

Address proofs MAY be revoked much like `did:key` proofs:

    @! John: did:key:z6MkCMyGw... <mailto:john@acme.com$->

Contrary to `did:key` proofs, address proofs MAY be reinstated, by separating multiple dates (in any order) to define intervals (see Address Changes):

    @! John: did:key:z6MkCMyGw...
        <mailto:john@acme.com$2024-01-01,-2026-05-01,.>

Address proofs that have been revoked can simply be omitted until recovered.

Apps MUST NOT send Gossip or Trust payloads to currently revoked addresses.


### Capabilities

Apps MUST support enumerating capability decorators after trigger definitions, even if they don't support triggers. Capabilities MUST be prefixed with a plus (`+`), with at least two base segments and an optional suffixed one separated by a colon (`:`):

    @! subject: object +base:base:suffix

Capabilities allow controlling what triggers can do in sandboxes. WebAssembly’s deny-by-default model exposes no file system, network sockets, system clocks, environment variables, process/thread primitives, inter-process communication, direct hardware access, or non-deterministic entropy sources. These must all be imported as part of setting up the virtual machine. Capabilities allow defining what to import:

    @! task.wasm: cid:f122009310... +clock:wall +net:outbound

Apps that support triggers SHOULD support the following baseline capabilities:

+--------------------+------------------------------------------------------+
| Capability         | Description                                          |
+====================+======================================================+
| `+clock:monotonic` | Non-decreasing millisecond clock                     |
+--------------------+------------------------------------------------------+
| `+clock:wall`      | ISO 8601 wall-clock time (host-local)                |
+--------------------+------------------------------------------------------+
| `+fs:read`         | Read-only file access, scoped: `+fs:read:/path`      |
+--------------------+------------------------------------------------------+
| `+fs:write`        | Write file access, scoped: `+fs:write:/path`         |
+--------------------+------------------------------------------------------+
| `+net:outbound`    | Outbound network connections (TCP/UDP/HTTPS)         |
+--------------------+------------------------------------------------------+
| `+random:secure`   | Cryptographically secure random bytes                |
+--------------------+------------------------------------------------------+
| `+env:read`        | Environment variables, scoped: `+env:read:prefix`    |
+--------------------+------------------------------------------------------+
| `+ipc:local`       | Local inter-process communication                    |
+--------------------+------------------------------------------------------+

Vendors MAY expose finer-grained or broader variants, and SHOULD namespace custom capabilities under `vendor:<name>:` to avoid collisions until enough vendors agree on the semantics. Heeding this suggestion will help avert the interoperability problems that plagued early internet browsers.


## Directives

Directives serve several purposes. The main one is to provide the messaging and legal discovery functionality needed to broadcast public notices and facilitate private exchanges during disputes, without depending on any infrastructure (see Messaging and Disputes). By extension, they enable delivering transactions to hard-to-reach recipients via routing intermediaries, and provide the reference syntax needed to streamline billing, reconciliation, and other tasks within and between systems.

Directives are like actions in spirit, with three important difference:

1. They get assigned to transaction recipients, rather than signers;

2. They get executed at transaction receipt time, rather than finalization time;

3. Their assignees MAY decide to ignore them, temporarily or permanently, since they did not expressly consent to them.

Consent is paramount, so apps MUST defer to ledger controllers on whether to honor directives. Apps MAY provide automations to do so.

A directive's object MUST start with an angle bracket (`>` or `<`), and MAY be followed by an optional filter:

    @! Community: > John

Optional filter arguments MAY use definitions as usual.


### Routing Directives

Routing directives instruct its assignee to forward a transaction as is, on top of the usual signed copy that may apply if they sign the transaction. What the routing directive means exactly depends on the filter it came with:

- Without a filter, the assignee SHOULD simply gossip the transaction to its required signers (see Finalization):

        @! CavemanFriend: >

- When the filter is a key in `did:key` format, they SHOULD gossip it to every counterparty they know that signed bookkeeping lines with that ledger key:

        @! *: > DeadLedger

- When the filter is a transaction ID as a file in `cid` format, they SHOULD gossip it to every counterparty they know that signed that transaction ID:

        @! *: > TransactionID

- When the filter is anything else, apps MUST ignore the routing directive as invalid, without any warning or error to avoid leaking information:

        @! *: > Invalid

An unfiltered relay enables delivering a transaction to a recipient that does not need to sign it, or to a hard-to-reach recipient that senders know often interacts with a routing intermediary.

Filtered relays enable delivering legal notices to their intended recipient when liquidating a ledger's positions (see Liquidations and Dead Ledgers), or follow-ups after a vote or a petition (see Optional Signers and Communities). Apps SHOULD confirm whether to honor filtered routing directives that have not been signed by a trusted arbitrator that _proves_ its standing (see Messaging Consent, Tacit Trust, and `did:key` Proofs). The latter check offers far more legitimacy guarantees than Rambos in uniform with a paper.


### Reference Directives

Reference directives provide the syntax needed to streamline dispute-related requests for information during legal discovery, and billing, reconciliation, and other tasks within and between systems. What the reference directive means exactly depends on the filter it came with:

- When the filter is a key in `did:key` format, apps SHOULD look up information about that key, such as the balance they hold with it, or the counterparties they know have signed bookkeeping lines with it:

        @! *: < DeadLedger

- When the filter is a transaction ID as a file in `cid` format, they SHOULD look up relevant information about that transaction, such as the contract, its envelope, its attachments, or its successive log entries and associated transactions:

        @! *: < TransactionID

- When the filter is anything else, apps MUST ignore the routing directive as invalid, without any warning or error to avoid leaking information:

        @! *: < Invalid

In the above, the filter is intended as a search hint and nothing else.

What to do with that search hint is context dependent. Legal discovery during a dispute is the canonical use-case this syntax was designed around, but it could just as well be used to automatically reconcile the payment and associated fees from an external source like an electronic bank statement, clear part or all of a specified ledger's balance, cancel a recurring contract, or simply reference a master service agreement when sending an invoice or extending a new contract.

Further, apps MUST NOT automatically share the result of these searches under any circumstances. App MAY draft replies to messages with references that have been signed by a trusted arbitrator that _proves_ its standing (see Messaging Consent, Tacit Trust, and `did:key` Proofs). These are the closest things this protocol has to off-graph search warrants, and end-users will no doubt be happy to not have to draft these replies manually. But directives are _optional_ as noted earlier, and on-graph search warrants are no exception (arbitrators and off-graph judges have other ways to get what they need), so apps MUST NOT send such replies without end-user review and express consent.

These filters are necessary and sufficient for the intended use-cases. Senders can always use plain language to explain what they'd like to see during legal discovery, and any other use-case that requires more granular filtering cannot be automated without vetting---so one may just as well run the queries needed to get the more precise reference that would actually allow full automations.
