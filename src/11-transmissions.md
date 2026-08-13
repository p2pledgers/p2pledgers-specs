# Transmissions

\epigraph{The content of any medium blinds us to the character of the medium.
}{Marshall McLuhan, Understanding Media (1964)}


## Endpoints

Transmission endpoints are functionally equivalent in that they share a common payload format, but the underlying transport they use creates minor differences between them.


### Endpoint Types

These specifications distinguish between three endpoint types as follows:

* Interactive, HTTP-like endpoints, which have RESTful semantics. These qualify as interactive in that senders can tell their payload arrived from the response code or a lack thereof (due to a timeout), and recipients can infer it did from whether the socket flushed cleanly---without a broken pipe or connection error. Beyond HTTP endpoints themselves, CoAP endpoints (schemes `coap` and `coaps`) would be HTTP-like endpoints if any apps were to implement them.

* Interactive, stream-like endpoints, which have a bidirectional session where the sender and recipient switch roles as they send data to one another. These endpoints have no HTTP-like semantics, but senders can infer a payload arrived from whether the socket flushed cleanly. Bluetooth and NFC endpoints are both stream-like.

* Non-interactive, email-like endpoints, which are fire-and-forget. Senders can only tell their payload was sent successfully. Senders might get an error when it did not arrive, but not reliably enough that they can count on it. File drop endpoints are all email-like.

In addition, these specifications distinguish between global endpoints, which are routable over the internet (public HTTP, email), and local ones, which are not (HTTP over a LAN, Bluetooth). Apps MUST NOT share local endpoint addresses during handshakes (see Handshakes).

These endpoints are all functionally equivalent. The slight differences between them tie into transmission queues and interaction flows. You know the identity key of the global HTTP endpoint you want to gossip a payload to, for instance, whereas you can't do anything useful with a local HTTP or NFC endpoint until the host tells you who it is. Beyond that, it's the exact same payload formats and responses, with gossip treating transmissions as blackboxes that just work (see Gossip).


### Endpoint Selection

End-users often enter addresses in their preferred communication order, so apps SHOULD monitor which addresses users enter first, SHOULD allow them to reorder those addresses, and SHOULD reflect their preferred ordering when communicating addresses.

Conversely, apps SHOULD monitor the order they receive addresses in, and SHOULD factor that in as a tie-breaker when selecting endpoints to send payloads to.

Beyond that:

* Apps MUST prefer the interactive endpoint that is in use, if any; and

* Apps SHOULD prefer local endpoints when one is available; and

* Apps SHOULD prefer interactive endpoints over non-interactive ones.


### Revoked Endpoints

Apps MUST NOT send payloads to addresses they know are currently revoked.

Apps SHOULD flag for review any payloads they sent to a revoked address before they learned it had been revoked. Recipients treat duplicate gossip payloads as network noise. There is as such no harm in re-sending them, but apps SHOULD let users decide whether to do so.


### HTTP Endpoints

Apps MUST support HTTP endpoints, and MUST use the standard `https` and `http` schemes as applicable when sharing such endpoints:

    https://<global_address>
    http://<local_address>:<port>

Where:

* `<global_address>` is an HTTP endpoint with a Fully Qualified Domain Name (FQDN). Apps MUST NOT allow using an IP address as a global HTTP endpoint, MUST NOT expose UPnP IGD to end-users, and MUST ignore HTTP endpoints passed using a non-local IP address. The FQDN requirement is intended as a static IP address guarantee to spare users and vendors a lot of UPnP IGD-related misery. (Power users that use UPnP IGD with a domain name will seldom need support.) Apps MUST use `https` with global HTTP endpoint addresses.

* `<local_address>` is an IP address broadcast via mDNS / DNS-SD / Bonjour or shared using a QR code or via NFC (see Pairing and Sessions). Apps MUST use `http` with local HTTP endpoint addresses to avoid certificate warnings.

* `<port>` is a port number. Apps SHOULD initialize local endpoints using port `0` to let the operating system assign them an ephemeral port number.

To send a payload as a request or a response to an HTTP endpoint, apps MUST:

0. Disable response buffering if applicable, to be able to catch broken pipe and connection errors.

1. Set the `Content-Type` header to `application/octet-stream`.

2. Set the `Content-Length` header to the wire-formatted payload's byte length (see Wire Format).

3. Start the body at byte offset `0`.

4. Output the raw bytes of the wire-formatted payload, without form field names.

5. Await a successful flush before marking the payload as sent.

Client apps MUST send gossip payloads via HTTP POST requests.

Host apps MAY piggyback on the open connection to return an HTTP response after successfully receiving a gossip payload via an HTTP POST request. Apps MUST set the `Cache-Control: no-store` header when sending such responses.

Host apps MAY chunk HTTP responses by setting an initial `Content-Type` header to `multipart/mixed; boundary=<boundary>` and flushing payloads one at a time to send more than one gossip batch as a single response (see Payload Formats).

Apps MUST limit HTTP response codes to exactly two:

* 403 (Forbidden), when rejecting a request early. An attacker would know their request got rejected because the connection got closed early, so a 403 does not reveal anything new or useful.

* 200 (OK), to signal that the payload arrived, whether it was accepted or not, to not disclose anything useful to a potential attacker.

Apps MUST output a handshake token as an HTTP response (see Handshakes):

* Upon receiving a valid challenge result that was configured using a valid but stale token (see Tokens and Challenges). Apps MUST send a 403 response code in this case, MUST use exponential back-off to throttle such responses so stale tokens can't be used as an attack vector, and MUST invalidate the token before the back-off can backfire as an attack vector (see Threat Management).

* Upon receiving an HTTP `GET /<endpoint_tag>` request, where `<endpoint_tag>` is the `Base64url`-encoded (without padding) endpoint's tag for an existing ledger.

* Upon receiving an HTTP `GET /` request, when a ledger is actively accepting proximity-based connections, since the endpoint's tag is then implicit.

Apps MAY cache handshake tokens sent on HTTP GET requests.

Apps MUST use the service type `_p2pledger._tcp` when advertising their local HTTP endpoints via mDNS / DNS-SD / Bonjour to actively accept proximity-based pairing requests (see Pairing).


### Bluetooth Endpoints

Apps SHOULD support Bluetooth endpoints on applicable devices, and MUST use the standard `ble` scheme when sharing such endpoints:

    ble:<service_uuid>:<psm>

Where:

* `<service_uuid>` is the service identifier. Host apps MUST set its value to the p2pledger-specific service identifier or to an ephemeral 128-bit UUID that they obtained to host a client's checkout session (see Sessions).

* `<psm>` is the protocol/service multiplexer allocated by the operating system at runtime.

The p2pledger-specific service identifier enables initiating handshakes to pair devices (see Endpoint Discovery). Apps MUST derive it using a standard UUIDv5 library, the `Namespace_DNS` constant defined in RFC 9562 or its later version, whose value is `6ba7b810-9dad-11d1-80b4-00c04fd430c8` at the time of writing, and the `p2pledger.local` domain name:

    Service_UUID = UUIDv5(Namespace_DNS, "p2pledger.local")

The latter formula yields `2b88bd30-24ef-514c-9500-f62295979bfa`.

L2CAP Connection-Oriented Channels (CoC) are the Bluetooth equivalent of raw socket streams, but without payload boundary management. Apps MUST therefore use the predefined length header when using Bluetooth (see Length Header).

Apps MUST await a successful flush before marking Bluetooth payloads as sent.

Host apps MUST output a handshake token when a client successfully connects to its service identifier (see Handshakes).


### NFC Endpoints

Apps SHOULD support Near-Field Communications (NFC) endpoints on applicable devices. At the time of writing:

* Android supports Host-based Card Emulation (HCE) Type 4 Tags, which can mimic payment cards directly. iOS exposes card emulation via the iOS 18.1+ NFC & SE Platform Entitlement, which requires a security audit and paying a fee. From there, apps can run their ISO 7816-compliant Java Card Applet that implements this protocol inside the secure element.

* Android and iOS both expose NFC reader APIs. Note that traditional app roles (which these specifications use in what follows) are flipped in NFC: host apps (NFC readers) are open and active, and process the transactions of client apps (NFC Type 4 tags) that may or may not be open.

* Practical speeds are slower than the theoretical 424 kbps or higher of modern devices, because NFC processes waste most of their time waiting for 255-byte long chunks to get scheduled by the OS---one chunk at a time, with a pause in between each one.

* Transmissions are better sent and received as Application Protocol Data Unit (APDU) byte streams to avoid OS-level interferences and signaling overhead that would make NFC slower still. APDU APIs are low-level and require apps to chunk and reconstruct payloads larger than 255 bytes. Apps MUST support chunking APDU byte streams sent in either direction.

With this in mind, NFC readers drive contactless NFC interactions in a typical card payment. The reader asks the card what it can do. The card returns a list of Application Identifiers (AIDs). The reader picks one. The card tells it what it needs. The reader gives it the details (such as amount, currency, timestamp, and nonce). The card then tells it how to get its card details. The reader asks for them, and wraps things up by asking for a signed payload.

Mobile host apps initiate that process. Typically, the host will see the client taking their phone out, so will anticipate needing NFC or a QR code. The host hits a button that enables both on their terminal and shows the order's details with the QR code and an invitation to tap their device with the screen oriented so the customer can review their order. The host will necessarily have asked if this is a card payment or not at this point, since that would require using the card terminal or another app. Apps MUST therefore select this protocol's AID as their initial command.

Apps MUST register themselves as a handler for the Application Identifier (AID) `F05032504C6564676572`---which corresponds to the `0xF0` proprietary AID prefix followed by the `P2PLedger` ASCII sequence---and use it for this protocol.

Mobile client apps kick in upon receiving the host app's first command: the OS opens the app's background NFC handler and lets it handle the request---without unlocking, if using biometric identification. Apps MUST require authentication if the OS doesn't require it as a matter of course.

The client app MUST respond with a standard `90 00` (Success) response on open.

The usual protocol checkout flow can then proceed with a twist: NFC is too slow to transfer anything more than metadata and a small signature envelope in under 300 ms---which is as long as typical users can hold a device still before shaky hands create connection problems.

As such, host apps MUST send a handle in its usual prefixed, Multibase-encoded format as the data payload of an APDU (see Handles). This effectively treats the NFC endpoint as a QR code reader that can also be used as a secure channel when the right conditions are met.

Client apps that don't have a pre-existing secure channel with their host app MUST terminate the NFC interaction by sending an APDU with a standard `90 00` response. Before sending it, client apps MUST wake up their app as needed to continue their interaction using another endpoint.

Apps that have a pre-existing secure channel with their host app SHOULD try to use it to complete the transaction. Either app can terminate the interaction by sending an APDU with a standard `69 85` (Conditions of Use Not Satisfied) code if anything goes wrong, with two cases. When the client app bails, it MUST wake up their app as needed to continue their interaction using another endpoint before sending it. When the host app bails, the client app MUST instead send a `90 00` response as an acknowledgement after waking up their app as needed, so the host app knows it can safely terminate the NFC field.

With this in mind, client apps MUST gossip a session request as the data payload of an APDU (see Sessions). Host apps MUST gossip the session data as the data payload of an APDU.

Client apps that end up with *one* contract whose value is beneath the ledger's maximum NFC expense threshold MUST sign this contract automatically, since the NFC tap with authentication is proof of intent enough. Client apps MUST bail in any other situation so their ledger controller can review what they're expected to sign.

Client apps MUST, if this contract's signature envelope is 1 kB or less, gossip the signature envelope (and only that) as the data payload of an APDU. Host apps MUST emit a beep and terminate the NFC channel upon completing their due diligence and signing (see Due Diligence), and MUST otherwise bail.

Host apps MUST NOT send their signed receipt via NFC---host apps MUST instead gossip it using another endpoint.

The 1 kB size limit deliberately rules out sending ML-DSA signatures. Vendors SHOULD coordinate to increase this limit when NFC becomes able to comfortably gossip an ML-DSA signed signature envelope.

Apps that support NFC SHOULD support using it for pairing (see Pairing). The flow is as above, but without any session, so it stops at the handle exchange.


### Email Endpoints

Apps SHOULD support email endpoints, and MUST use the standard `mailto` scheme when sharing such endpoints:

    mailto:<user>+<tag>@<domain>

With the usual email `<user>`, `<tag>`, and `<domain>` semantics.

Apps MUST add an email subaddress (the `<tag>` in `<user>+<tag>@<domain>`) when the ledger controller forgets to add one, and SHOULD create a filter that moves emails with that subaddress to a dedicated folder automatically. This ensures ledger controllers can keep using their email address normally. Apps SHOULD NOT use `+p2pledger` or anything based on their app's name for this, since it would be a dead giveaway that could end up being used as a tracking beacon.

To send a payload to an email endpoint, apps MUST create a multipart email and add it as an attachment. Apps MUST attach at most one payload per email.

Apps MUST await a successful submission acknowledgment before marking email payloads as sent.

Email servers sometimes (though not always) send delivery error messages. Apps SHOULD catch such error messages by scanning for the email subaddress they are tracking, SHOULD ignore the offending addresses until the next handshake, and SHOULD ignore serial offenders permanently.

Note that email clients and servers might block or flag emails with no subject and no content as suspicious. Apps SHOULD therefore set a subject and a body, but SHOULD also be wary of revealing anything useful about the payload in the email's subject or body since email endpoints use an unencrypted channel that leaks metadata. Apps MAY use a *local* LLM for this purpose---have one write a story one paragraph at a time, for instance.

Apps MUST output a handshake token as an email response (see Handshakes):

* Upon receiving a valid challenge result that was configured using a valid but stale token (see Tokens and Challenges). Apps MUST use exponential back-off to throttle such responses so stale tokens can't be used as an attack vector, and MUST invalidate the token before the back-off can backfire as an attack vector (see Threat Management).

* Upon receiving an email that contains their `base64url`-encoded (without padding) endpoint tag as its first line with no attachment.

Apps MUST accept payloads sent by unknown senders, since that is necessary for handshakes and receipt delivery, but MUST NOT send gossip payloads in response to incoming gossip payloads sent by unknown senders, and MUST NOT initialize a handshake with them either. Apps MUST instead let them start a handshake. This ensures apps that lack an email endpoint can send one-way updates to apps that have one.

Apps MAY offer to keep emails with handshake requests and payloads as a backup, and SHOULD otherwise delete protocol-related emails after processing (received, but also sent, since those use up space too).

Note that corporate email gateways tend to silently drop emails that contain encrypted payloads they cannot inspect. Vendors that want to work around the latter SHOULD coordinate and define custom schemes that standardize embedding payloads inside media files. (Steganography libraries have too many shortfalls at the time of writing, but the field is evolving quickly.)


### File Drop Endpoints

The early fanfare about IPv6 was that it would once again allow two devices to connect directly. NAT was viewed at the time as a hacky workaround to not run out of 32-bit IPv4 addresses. The accidental security NAT provided soon became a feature---you don't want botnets port scanning mobile phones or apps draining phone batteries flat by waking them up constantly.

Carriers are still dropping unsolicited inbound connections decades later, and will do so indefinitely. This comes on top of restrictive firewalls and mobile operating systems that shut down sockets.

True global peer-to-peer transport options are non-existent as a result. Every option depends on a relay to establish a connection, and every option depends on a mailbox to deliver payloads when two mobile apps are not in use at exactly the same time. Every option is re-inventing email with a twist. These endpoints are thus all non-interactive and fire-and-forget for our purpose.

This protocol is able to accommodate incompatible endpoint semantics to a large degree: what matters for interoperability is that endpoints are successfully sending payloads to one another, not the specific signaling they use as they interact with third-parties. RESTful endpoints typically have stable APIs to avoid developer uproar, so any well-tested implementation will work. Those with stream-like semantics (like WebRTC) are trickier: apps SHOULD simply try them, and ignore those that don't work as dysfunctional until the next handshake or some other random event. Vendor-prefixing of schemes is as such OPTIONAL.

With this said, three rules are needed to avoid scattering schemes:

1. Apps MUST replace dots (`.`) with dashes (`-`) inside schemes derived from domain names, and MUST NOT use custom schemes with dots. RFC 3986 technically allows dots in URI schemes, but support outside of OS-level parsing and app routing is scarce due to fragile regular expressions and the abuse of custom schemes in phishing scams. Contracts get rendered outside of apps (see Contract Files), so dots in URI schemes are best avoided.

2. Cloud-based web folders SHOULD be declared using their domain as the scheme, and the unique handle as the locator:

        <scheme>:<handle>
        drive-google-com:AbCdE...

3. Social media channels and other social drop sites SHOULD be declared using their standard scheme if one exists, or using their domain as the scheme when not, and the valid handle (in any valid format) as the locator:

        <scheme>:<handle>
        facebook-com:john
        x-com:john
        whatsapp:+1-123-456-7890
        tg:john
        matrix:@john:acme.com
        matrix:u/john:acme.com
        nostr:npub180cvv07...
        nostr:john@acme.com

Apps MUST support optional formatting of phone numbers for human-readability. Storing them in E.164 format is fine.

Apps MUST NOT exceed the payload sizes specific to the file drop endpoint being used (such as the 128 kB size limit on most Nostr relays). Too large files can always wait until the next interaction.

Endpoint semantics will depend on the exact endpoint. APIs are usually RESTful, and thus HTTP-like, if with a drop point. WebRTC and local radio-based meshes are stream-like for their interactive half, but delivering payloads to mobile devices that can't reliably wake up and open a socket depends on a drop point.

Endpoints SHOULD catch delivery error messages when applicable and handle them the same way email endpoints do: ignore the offending addresses until the next handshake, and ignore serial offenders permanently.

Apps SHOULD NOT add handshake token semantics to file drop endpoints, since few of them can accommodate receiving no payload or a zero-length one anyway.

Beyond that, apps MAY support file drop endpoints as they see fit.


## Endpoint Discovery

Apps discover one another's endpoint addresses:

* Actively, through proximity-based connections (HTTP advertised on local area networks, Bluetooth, NFC; see below); or

* Through handles shared using QR codes, via NFC, inside signature envelopes such as those in contract files (see Handles); or

* Through handshakes (see Handshakes).

Apps MUST NOT accept active, proximity-based connections without express user consent. Mobile apps MUST require a session-based checkout (see Sessions) or hitting a Pair button (see Pairing) before advertising their endpoints. This is to ensure endpoint discovery can't be abused for tracking. Desktop apps MAY be more lenient and keep their local endpoints on and advertised at all times.


### Handles

Discovery handles are flat, integer-indexed CBOR maps that enable apps to share endpoint addresses and an optional session:

    {
      0: [
        [<endpoint_tag>, <endpoint_address>],
        ...
      ],
      1: [<host_tag>, <session_id>]
    }

Where:

* `<endpoint_tag>` is the endpoint's tag (see Endpoint Tags).

* `<endpoint_address>` is the endpoint's address (see Endpoints).

* `<host_tag>` is the device identifier of the session holder (see Host Tags).

* `<session_id>` is the raw 32 bytes of a session's identifier (see Sessions).

The `<host_tag>`, `<session_id>` tuple is optional. Apps MUST NOT include one while pairing (see Pairing), and MUST add one for session-based checkout.

Apps MUST share discovery handles as Multibase-encoded payloads prefixed with the custom `p2pledger:` scheme, and MUST register themselves as a handler for the latter. This format enables sharing discovery handles using QR codes, via NFC, and as links in other contexts, using the same, consistent format.

Apps MUST make the `p2pledger:` prefix compatible with the encoding alphabet of the discovery handle that follows it. In particular, apps MUST uppercase the `P2PLEDGER:` prefix when using `Base45`:

    p2pledger:u<base64url_cbor>
    P2PLEDGER:R<base45_cbor>

Apps MUST use `Base45` when encoding discovery handles shared in QR codes. It was designed to allow using Alphanumeric mode (5.5 bits per character) instead of Byte mode (8 bits per character) inside QR codes.

Typically, an app that consumes a discovery handle will open a connection using one of the advertised endpoints and do what it needs to do. The only exception is NFC when the endpoint allows completing a transaction (see NFC Endpoints).

Apps SHOULD keep discovery handle sizes including their `P2PLEDGER:` prefix to 221 characters at most when shared using QR codes. It corresponds to a 140-byte CBOR before `Base45`-encoding. The resulting Version 8-M QR codes (or smaller) ensure fast scanning even when in suboptimal conditions. 

Apps SHOULD keep discovery handle sizes under 255 characters when shared via NFC so they can fit in a single APDU. It corresponds to a 183-byte CBOR before `Base64url`-encoding without padding.


### Endpoint Tags

Endpoint tags are ledger-specific endpoint identifiers that enable ledgers to directly engage with ledgers they've already established a secure channel with.

An endpoint's tag is the first (leftmost) four bytes of the fingerprint of the transport key it is associated with for the purpose of issuing handshake tokens (see Fingerprints and Handshakes). Local endpoints typically use a common key for this purpose.

This specific key is not used for encryption, so tends to be more static than the keys used to encrypt handshake payloads. That makes it useful to identify endpoints without being so static it becomes a long-term tracking beacon.

Apps MUST complete a handshake before using an endpoint whose tag they do not recognize. Periodically rotating their handshake token keys therefore enables apps to force other apps they interact with to rotate their keys.


### Host Tags

Host tags are device-ledger-pair specific identifiers that enable ledgers that are synchronized to distribute session management among them (see Sessions and Synchronization).

Apps MUST compute host tags as follows:

    Hash(<endpoint_tag> || <book_id>)

Where:

* `Hash` is the canonical hash algorithm (see Identifiers).

* `<endpoint_tag>` is the HTTP endpoint tag that the session host disclosed to synchronize session state.

* `<book_id>` is the device-ledger pair's unique identifier (see Book IDs).

Host tags enable this protocol to natively support:

* Local sessions with local interactions: the terminal holds its own sessions and manages all of its checkout interactions directly.

* Local sessions with remote interactions: the terminal holds its own sessions, while delegating part or all of its checkout interactions (like the server with the store's e-commerce website).

* Remote sessions with local interactions: the terminal delegates sessions to another device (like the shop's main computer), but manages part or all of its checkout interactions directly (so customers can use Bluetooth or NFC).

* Remote sessions with remote interactions: the terminal delegates sessions and its interactions, and gets notified as needed.



## Fingerprints

Fingerprints are relationally salted tokens designed to identify payloads sent by known counterparties without revealing their ledger key to observers.

Conceptually, fingerprints are like Truncated Key Identifiers, with the twists that the payload is based on the public key pair and the transmission channel that ledgers are interacting on instead of one key, and the hash algorithm is derived from the recipient's public key.

To compute a recipient's fingerprint, a sender's app MUST compute:

    Hash(<RecipientKey> || Hash(<SenderKey> || Hash(<RecipientAddress>)))

Where:

1. `<RecipientKey>` and `<SenderKey>` are the recipient's and the sender's raw public key bytes without Multicodec prefixes.

2. `<RecipientAddress>` means the recipient's address scheme and locator exactly like the recipient shared them with the sender, as raw UTF-8 bytes (in other words, preserve the case, and ignore address proof arguments; see Bootstrap Handles and Address Proofs).

3. `||` means concatenating raw bytes as is.

4. Hash is the algorithm derived from the recipient's ledger key. The codec in the key's `did:key` format reveals its type, which allows to deterministically map that key to the hash algorithm it uses for signing (see Curve Selection). P-256, P-384. and Ed25519/X25519 use SHA-256, SHA384, and SHA-512 respectively.

Apps MUST precompute, store, and index the first four bytes (leftmost) of all counterparty fingerprints for fast look-up. Four bytes are enough to guarantee that few if any collisions inside a set will exist, and allow an index layout optimization in database engines that offer Hash indexes.

Apps MUST NOT store the full fingerprint, as this would invite data breaches as a quick way to build a rainbow table.

Fingerprints allow an encrypted payload's recipient to determine its sender without trying every public key until they find one that works (see Payload Format), and enable ledgers to ask each other about the creditworthiness of a ledger without revealing its identity to those who don't know it (see Trust). In both cases, a simple look-up reduces the search space to a set small enough (typically one candidate key, rarely more) that recomputing the hash of each candidate key is perfectly acceptable.

Apps MUST compute new fingerprints when they learn about new or rotated keys.

Apps MUST temporarily retain old hashes when rotating keys (see Key Rotations), and MUST compute each counterparty's new fingerprint _before_ letting them know about the key rotation.


## Payload Format

The Gossip and Trust protocols (see Gossip and Trust) minimize interactions by batching payloads. Both treat batched payloads as atomic units of transmission and assume the transport will just work.

Apps MUST envelope batched payloads in flat CBOR maps (RFC 8949) that omit their optional self-describing tag. The exact Gossip and Trust payloads are different and detailed below.

These envelope formats pack the information needed to check the integrity of payloads before processing, without embedding predictable meta-information like MIME file headers or zip magic numbers or CBOR self-describing tags that could be used as a plaintext oracle or crib during cryptanalysis of the payload.

Apps MUST encrypt this CBOR map using HPKE (see Secure Channels).

Apps MUST wireframe this encrypted payload by adding the first 4 bytes of the sender's fingerprint for that transmission channel (see Fingerprints), so the payload's recipient can zero in on how to decrypt the payload without trying every key:

    [ 4-Byte Fingerprint ] [ HPKE Ciphertext ]

The fingerprint's high entropy and position make it look like encrypted data to a first time observer. In principle, it could be used as an oracle by analyzing traffic over time. In practice, the fingerprint is unique per counterparty pair and per transmission channel, and ledgers will have revealed their relationship to a traffic analyzer anyway. Plus, either counterparty can rotate their ledger key to change the fingerprint (see Key Rotations).

Most communication transports with be happy with this fingerprinted payload as is. Lower level ones, like Bluetooth L2CAP byte streams, need apps to manually communicate payload boundaries. In such cases, apps MUST add an extra 4-byte, big-endian unsigned integer header with the fingerprinted payload's byte size:

    [ 4-Byte Size ] [ 4-Byte Fingerprint ] [ HPKE Ciphertext ]

Apps that want to support exotic transports like radio-frequency-based ones may need to chunk payloads and handle the stream fragmentation and reassembly.


### Gossip Payloads

Gossip payload maps MUST correspond to a batch of files, with each file's key corresponding to its string-encoded Content Identifier (see Identifiers), and each value corresponding to an array containing the file's name followed its raw bytes:

    { <cid>: [<filename>, <bytes>], ... }

Each file MUST correspond to a contract, an envelope, or a contract attachment. Apps MUST check the integrity of the file recieved using the hashes encoded in the cids, and MUST request files to be re-issued when appropriate.

Apps SHOULD be mindful of file sizes when batching gossip payloads. Contracts and envelopes are always fair game to batch since they're small text files, but apps SHOULD NOT batch large contract attachments to inappropriate endpoints. In particular, apps SHOULD NOT batch attachments larger than what a typical mobile device can download in a second when gossiping by email, phone notification, or social media chat, to avoid needlessly draining batteries. Apps SHOULD instead gossip large files through an interactive endpoint at the earliest opportunity. Apps MAY offer UI to force sending a large attachment to override this default behavior.


### Trust Payloads

Trust request payload maps MUST be an envelope with three fields:

- `query`: contains the root `/score` authorization signed by the issuer, with optional `/sign` authorizations as required (see `/score` Authorizations and `/sign` Authorizations), each encrypted using a symmetric key.

- `chain`: contains `/score` authorizations signed by requesters as required, with optional `/sign` authorizations as required, to chain trust queries.

- `keys`: contains a map that pairs the fingerprints of the intended scorers with their respective copy of the symmetric key, encrypted for its intended scorer tied to that fingerprint using HPKE _Base Mode_. The `info` parameter MUST contain the raw bytes of the intended scorer's ledger key so the symmetric key is contextually bound to it.

    {
      "query": [ <encrypted_authorization>, ... ],
      "chain": [ <authorization>, ... ],
      "keys": { <fingerprint>: <encrypted_key>, ... }
    }

This setup maintains the privacy of the issuer being scored and allows peers to police abuses. Only the intended scorers know the fingerprints that the issuer uses to interact with them, so only they can decrypt the `/score` authorization in `query`. The latter scopes the request to an intended recipient, and limits it in time according to the scorer's wall clock (see Wall Clocks). Lastly, the public authorizations in `chain` ensures ledgers can authenticate every chained requester before chaining further, and police abuses as needed.

Trust response payload maps get batched as they arrive through chained streams, and MUST correspond to a batch of encrypted scores (see Trust Scores), with each key corresponding to the fingerprint of the score's assessor as it was passed in the request, and each value corresponding to the encrypted score of the request's original issuer, encrypted using HPKE _Base Mode_. The `info` parameter MUST contain the raw bytes of the intended recipient's ledger key so the symmetric key is contextually bound to it:

    { <fingerprint>: <encrypted_score>, ... }


### Steganography

Apps MAY encode wireframed payloads (see Payload Format) inside media files to overcome hostile transmission contexts.

Steganography is vendor-driven, but needs a mention because transport channels can face delivery problems. Corporate email gateways routinely block encrypted payloads they can't open and inspect, for instance. The workaround is to give corporate security your private key, but that is not always sane or practical.

On the flip side, steganography algorithms are many, not always maintained, and not always compatible for the same name (see `f5stegojs` and `F5Py`). So there is very little to latch onto except conventions on the address proof arguments to use (see Address Proofs).

Apps MUST reserve and recognize the `stego` address proof argument to signal a steganography requirement, and MUST NOT send payloads to that address if they cannot honor that steganography requirement. The `stego` argument MUST contain a case-insensitive steganography algorithm identifier. Any other argument used alongside it is vendor or algorithm specific.

Apps SHOULD namespace steganography identifiers behind a `vendor:<name>:` prefix to avoid collisions until enough vendors agree on the semantics. Heeding this suggestion will help avert the interoperability problems that plagued early internet browsers.

The goal here is getting past the email filter, not cryptographic obfuscation. If you're concerned about the latter, you shouldn't be using a fingerprint to know which ledger sent you a transaction. Also, local transports like WiFi or Bluetooth don't need steganography, since apps are communicating directly.


## Transmission Queues

Apps MUST maintain transmission queues for incoming and outgoing payloads. The Gossip and Trust sections cover the specific functionality needed for each one. 

Apps SHOULD follow transmission queue best practices---exponential back-off, jitter, failure thresholds, time-to-live, eviction, purging, etc. You know the drill if you've made it this far into this chapter.
