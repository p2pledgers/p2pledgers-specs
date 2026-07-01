# Parsing

\epigraph{Every sign by itself seems dead. What gives it life? In use it is alive. Is life breathed into it there? Or is the use its life?
}{Ludwig Wittgenstein, Philosophical Investigations (1953)}

The takeaway for non-technical readers: This section covers the detailed syntax and parsing rules for instructions that had been glossed over until now.


## Continuations

Instructions MAY spread over multiple lines by indenting them more than the initial line as noted earlier.

    @! Subject: Object
    @!  continuation

Spaces before continuations are not significant. Apps MUST join each initial instruction line with its continuations lines, all stripped of leading spaces, using _one_ space (`\x20`) as separator before parsing the whole instruction.

This means that the following:

    @!    Subject: Object
    @!        continuation

Joins to:

    Subject: Object continuation

Instruction continuation collection stops when:

1. An instruction line has the same indentation or less as the _initial_ line:

        @! Subject: Object
        @!   continuation
        @!  still a continuation
        @! New subject: ...

2. A new instruction block starts after non-instruction lines:

        @! Subject: Object
        @!   continuation

        @!     New subject: ...

The above rules mean that the following:

    @! Subject: Object
    @!   continuation
    @!   not a new subject: ...

Joins to:

    Subject: Object continuation not a new subject: ...


## Parsing Rules

Apps MUST parse instructions using the "lex, then parse" strategy that follows.

Apps SHOULD report as many errors as they reasonably can, not merely the first one. At minimum, wrap up the ongoing step before bailing. Discovering errors one at a time is about as vexing as awaiting an hourly bus that left early.

Apps SHOULD provide adequate context when reporting errors.

Apps MUST NOT allow signing or executing a contract if any of the instructions in it produce a parse error, since anything short would be undefined behavior---but synchronization between devices could slip such a transaction into logs, so apps MUST also support logging and rescuing them (see Synchronization).

These specifications' repository [@P2PLedgersRepo] contains a Rust/Pest-based, unit-tested implementation of steps 1-7 below using the reference PEG grammar. Feed it a normalized contract, and it will return a list of parsed instructions or a list of errors. The library is fast, memory safe, and can be compiled to WebAssembly or to a shared library via C-compatible FFI or JNI. It can thus be used as is in most projects.


### Step 1: Process Blocks

Start by collecting instruction blocks in the contract. Locate the next line that starts with optional spaces and an at-bang (`@!`), then continue adding instruction lines with the same at-bang indentation to that block. Repeat to get a list of blocks.

This example should produce three blocks, the first one with three instruction lines, the other two with a single instruction line:

      @! Subject1: Object1
      @!   <some:proof> +fs:read:/path; param=value
      @! Subject2: "Object2" 1_000 Custom Unit ; comment

      @! Subject3: Object3
           @! Subject4: Object4

Normalize each block before processing its continuations. Remove spaces before the at-bang, remove the at-bang itself, and normalize tabs before the resulting instruction line so each tab fills up to four spaces.

The first block in our earlier example becomes:

    Subject1: Object1
      <some:proof> +fs:read:/path; param=value
    Subject2: "Object2" 1_000 Custom Unit ; comment


### Step 2: Process Continuations

Process the continuations in each block. The first line's indentation serves as the reference. Collect each line with a greater indentation as a continuation of this first line. Join the collection with a space. Repeat to get a list of normalized instruction strings.

The first block in our earlier example becomes:

    ...
    Subject1: Object1 <some:proof> +fs:read:/path; param=value
    Subject2: "Object2" 1_000 Custom Unit ; comment
    ...


### Step 3: Slice Instructions

Next, slice each instruction to get its subject, directive indicator, object, proofs, capabilities, and parameters using the parsing grammar (see Parsing Grammar). Collect a parse error for and skip any instruction that whose slicing fails. Repeat to get a list of sliced instructions.

The first block in our earlier example might become:

    [..., {
      subject: "Subject1",
      directive: "",
      object: "Object1",
      line: [],
      proofs: [["some", "proof"]],
      capabilities: [["fs:read", "/path"]],
      parameters: [["param", "value"]]
    }, {
      subject: "Subject2",
      directive: "",
      object: "\"Object2\"",
      line: ["1_000", "", "", "", "", "Custom Unit"],
      proofs: [],
      capabilities: [],
      parameters: [["comment"]]
    }, ...]


### Step 4: Parse Instructions

We can now parse and post-process every field of every instruction. Collect a parse error for and skip any instruction that fails to parse.

Locate all fields that start with a quote delimiter. Deduplicate the delimiters inside them and strip the two outer delimiters.

Post-process the line amount and unit if needed. The line might have an infixed unit inside it that needs to get stripped, or a trailing `.-` or `-` that needs to get converted to `.00`. The unit might have separate ISO, prefixed, infixed, suffixed, and (custom) unit parts that also need processing.

The amount grammar accepts a prefixed, infixed, and suffixed unit at the same time. Collect a parse error for and skip any instruction that combines infixed and suffixed units, since doing so is meaningless (see Unit Clusters).

Proof arguments also need processing: the date, if any, need validating to make sure it's a valid date.

Post-process other fields as called for: cast amounts, treat parameters with no value set as a boolean `true` to mimic RFC 8941 behavior (the parser will set an empty string as value for `name=`), and anything else that needs attention due to e.g. custom capabilities. Instructions need a type annotation for later use---default it to unknown.

Then, collect a parse error for and skip any instruction that contains an empty subject, proof scheme, proof locator, capability part, or parameter name. An empty object is a parse error unless the instruction has a routing directive indicator (`>`). An empty parameter value is fine---it's shorthand for boolean `true`.

The first block in our earlier example might look like:

    [..., {
      type: "?",
      subject: "Subject1",
      directive: "",
      object: "Object1",
      line: [],
      proofs: [["some", "proof"]],
      capabilities: [["fs:read", "/path"]],
      parameters: [["param", "value"]]
    }, {
      type: "?",
      subject: "Subject2",
      directive: "",
      object: "Object2",
      line: [1000, "Custom Unit"],
      proofs: [],
      capabilities: [],
      parameters: [["comment", true]]
    }, ...]


### Step 5: Process Subjects

We can now start processing definitions, starting with identities.

Collect instructions with a subject that _is not_ a key in `did:key` format, _nor_ a file in `cid` format, _nor_ `*`, `-`, or `.`, and whose object _is_ a key in `did:key` format _without_ any bookkeeping line or directive indicator:

    @! Subject1: did:key:z6MkFEB7V...

These are unequivocally identity definitions. Annotate each as a definition---collect a duplicate error for and skip applicable instructions as you go along.

Identities cannot have capabilities, so collect an invalid type error for and skip any identity definition that does:

    @! Invalid: did:key:z6MkHFkSv... +net:outbound

(Parameters could have been used as comments, so leave those as is.)

Partially process identity definitions. Loop over _instructions_, and match their subject against identity definition subjects. Apps MUST NOT process any other field at this stage, because it would invite instruction injection.

Definition subjects MUST appear exactly as defined for the substitution to be valid. Apps SHOULD try to catch errors like mismatched casing, and highlight those with warnings.

Track unused definitions while processing---we'll warn about them later.

During processing, collect an invalid type error for and skip any instruction whose subject _and_ object are a key in `did:key` format with no bookkeeping line. Mind that this is for all instructions, not just those being processed:

    @! "did:key:z6MkFEB7V...": "did:key:z6MkHFkSv..."   ; Malicious

The first block in our earlier example might now look like:

    [..., {
      type: "?",
      subject: "did:key:z6MkFEB7V...",
      directive: "",
      object: "Object1",
      line: [],
      proofs: [["some", "proof"]],
      capabilities: [["fs:read", "/path"]],
      parameters: [["param", "value"]]
    }, {
      type: "?",
      subject: "did:key:z6MkHFkSv...",
      directive: "",
      object: "Object2",
      line: [1000, "Custom Unit"],
      proofs: [],
      capabilities: [],
      parameters: [["comment", true]]
    }, ...]


### Step 6: Process Definitions

Now collect all instructions with a subject that _is not_ a key in `did:key` format _nor_ `*`.

These could denote all sorts of data entry problems, so process errors first:

- If the subject is `-` or the object is `*` or `.`, collect a reserved error for and skip the instruction:

        @! -: Malicious
        @! Malicious: *
        @! Malicious: .

- If the subject is a file in `cid` format, collect an invalid type error for and skip the instruction:

        @! cid:f01551220df766...: Malicious

- If the object is `-`, or the instruction has a bookkeeping line, then it is an action whose subject is undefined, so collect an undefined error for and skip the instruction:

        @! Undefined: -
        @! Undefined: "did:key:z6MkHFkSv..." 100 USD

- If the object is a file in `cid` format with a bookkeeping line, collect an invalid type error for and skip the instruction:

        @! Invalid: cid:f01551220df766... 100 USD

Other collected instructions are unequivocally definitions. Annotate each as a definition---collect a duplicate error for and skip applicable instructions as you go along. Then annotate every unannotated instruction as a directive if a directive indicator is present, else as an action.

Process all definitions in one pass. Loop over _instructions_, and match their object, proof schemes, proof locators, and parameter values against definition subjects that are not `.` (see Transaction Titles). As with identities, replace exact matches with the definition's object only, and apps should be helpful.

Apps MUST treat definitions as string literals. In plain text, your outer loop **must be** the instructions, not the definitions, so as to process instruction fields at most _once_. This ensures definitions can't bind other definitions by accident---a desirable property to limit the surface for instruction injection.

Track unused definitions while processing as earlier. Then, issue an unused definition warning for each unused definition whose object is _not_ a file in `cid` format. Unused files can be simple attachments. The rest indicates data entry problems.

The first block in our earlier example might now look something like:

    [..., {
      type: "action",
      subject: "did:key:z6MkFEB7V...",
      directive: "",
      object: "cid:f01551220df766...",
      line: "",
      proofs: [["did:key:z6MkCDkFW...", "zdpu6vTR4..."]],
      capabilities: [["fs:read", "/path"]],
      parameters: [["param", "final value"]]
    }, {
      type: "action",
      subject: "did:key:z6MkHFkSv...",
      directive: "",
      object: "did:key:z6Mk3ZXR3...",
      line: [1000, "Custom Unit"],
      proofs: [],
      capabilities: [],
      parameters: [["comment", true]]
    }, ...]


### Step 7: Structural Validation

With directives and actions identified, and all definition references in them processed, we can now turn our attention to structural validation:

- Collect an invalid type error for and skip any directive whose object is not empty, or a key in `did:key` format, or a file in `cid` format:

        @! did:key:z6MkFEB7V...: > -
        @! did:key:z6MkFEB7V...: > Invalid

- Collect an invalid type error for and skip any directive whose object has a bookkeeping line, a proof, or a capability:

        @! did:key:z6MkFEB7V...: > "cid:f01551220df766..." 100 USD
        @! did:key:z6MkFEB7V...: < "cid:f01551220df766..." +clock:wall

- Collect an undefined error for and skip any action whose object is _not_ a key in `did:key` format _nor_ a file in `cid` format:

        @! did:key:z6MkFEB7V...: Undefined

- Collect an invalid type error for and skip any action whose object is `-` with a bookkeeping line, a proof, or a capability:

        @! did:key:z6MkFEB7V...: - 100 USD
        @! did:key:z6MkFEB7V...: - +clock:wall

- Collect an invalid type error for and skip any action whose object is a key in `did:key` format without a bookkeeping line or with a capability:

        @! did:key:z6MkFEB7V...: "did:key:z6MkHFkSv..."
        @! did:key:z6MkFEB7V...: "did:key:z6MkHFkSv..." 100 USD +clock:wall

- Collect an invalid type error and skip any action whose object is a file in `cid` format with a bookkeeping line.

        @! did:key:z6MkFEB7V...: "cid:f01551220df766..." 100 USD

Apps MUST NOT validate proofs at this point. The signatures and authorizations might not all have been acquired yet, or have been deleted (see Integrity). The time to verify addresses and block transactions with invalid `did:key` proofs is at signing time (see Due Diligence).

Instructions are all parsed at this point, with definitions, directives, and actions all well formed.

The last sanity check is on the amounts. Verify that amounts won't produce an overflow or some other amount related quirk upon signing the transaction (see Bookkeeping Lines). Collect an invalid data error for and skip all bookkeeping line actions if that final check fails.

Now is the correct time to report warnings and errors---and bail if needed.


## Parsing Grammar

The PEG-based reference version is under the prose-based human version.


### Human Version

The syntax is intended to adapt to end-users and tolerate non-ambiguous inputs that a compiler or a shell would reject. End-users write apostrophes without second thoughts and correctly fume at tools that won't let them. So we allow extraneous whitespaces everywhere and rip out superfluous quotes everywhere.

Further, and contrary to the usual left-to-right parser that yells at you about the flimsiest error, this parser looks far ahead, and reclassifies anything it fails to parse as data, rather than producing an error.

Instruction subjects, objects, line units, schemes, locators, proof arguments passed as query strings, capability parts, parameter names, and parameter values (collectively, tokens) can all be wrapped in VB-style quotes (see Quotes). Other quotes and any other character inside tokens (including whitespace) are treated as literals.

Empty values that don't trigger parsing errors get caught after slicing (see Parsing Rules step 4).

Quotes MUST enclose a whole value, and allow using any character inside them, including those that are normally disallowed. An unterminated or improperly escaped quote usually leads to a parse error. More rarely, an unterminated or improperly escaped quote delimiter leads to a valid instruction, and a likely undefined error.

    @! "Parse: Error
    @! "Par"se: Error
    @! Subject: Object 100 "also object <scheme:locator>
    @! "Why: Step 6": Requires 100 Literals   ; Malicious

Proofs start with a whitespace, followed by a `<`, a scheme, `:`, a locator, up to two optional arguments prepended with a `$`, and `>`. An unquoted scheme MAY be a key in `did:key` format, and an unquoted locator MAY be a file in `cid` format. A scheme, locator, or proof argument MUST NOT contain `;`, `+`, `:`, `<`, `>`, `$`, or whitespace characters, with an exception on `:` made for the latter two patterns. The first ISO 8601 extended-formatted proof argument MUST be captured as the date, with an optional `-` sign prepended to it. The other proof argument, if any, MUST be captured as arguments passed as a query string. Schemes, locators, and proof arguments MAY have whitespace around them.

    @! Subject: Object <did:key:z6MkFEB7V...:cid:f01551220df766...>
    @! Subject: Object < "scheme" : "locator" $ "argument" >

Capabilities start with a whitespace, followed by a `+` and a capability part, with any number of `:` followed by another part after that. Unquoted parts MUST NOT have  `;`, `+`, `:`, `<`, `>`, or whitespace characters in them, and parts MUST NOT have whitespace around them. The capability base is at least two parts long, and the tail is the final part when there are more than two parts.

    @! Subject: Object +"base":"base":"base":"tail"

Bookkeeping lines start with a whitespace. The parser peeks ahead and tries to match a leading ISO code. Failing this, it'll try to find a trailing ISO code. It tries to identify prefixed, infixed, and suffixed units around the amount. An ISO code before or after makes the latter optional. If all else fails, the parser tries to match an amount, a whitespace, and trailing non-decorators after that as a custom unit. A unit MUST be non-empty. Amounts and units MAY have whitespace around them.

    @! Subject: Object 100 USD

A prefixed unit MUST be one or two capitalized ASCII letter followed by a `$` (`U$`, `US$`), or a capitalized ASCII letter with a slash and an optional dot (`S/`, `B/.`), or two consonant ASCII letters and an optional dot (`Fr`), or a single non-amount non-delimiter character (`$`, `€`).

    @! Subject: Object $100

An infixed unit MUST be a single non-amount non-delimiter character (`$`, `€`).

    @! Subject: Object 1€00

A suffixed unit MUST be a word formed with non-amount non-delimiter character, with optional dots in between two characters, and an optional trailing dot if longer than two characters. That covers sensible suffixes. Anything longer or different gets processed as a custom unit per above.

    @! Subject: Object 100 €
    @! Subject: Object 100 19L Buckets

Amounts MUST look like typical accounting values (see Bookkeeping Lines), with a potential sign, digits that don't start with zero unless a dot follows it, no more than one dot before or in between digits, and optional underscores between pairs of digits. A trailing `.-` or `-` MAY be used as a shorthand for `.00`. Non-decimals, exponents, and mathematical formulas are invalid.

    @! Subject: Object USD $1.50
    @! Subject: Object £1p50    ; 1.50 GBP
    @! Subject: Object 1€-      ; 1.00 EUR
    @! Subject: Object $.02     ; USD .02
    @! Subject: Object +1.00 "Unit"

Parameter names start after a `;` and stop at the first `=`, if any, with their parameter value after the `=`. Parameter names and values MAY have whitespace around them.

    @! Subject: Object ; "Parameter" = "Value"; "Parameter"

Subjects MAY be an unquoted key in `did:key` format followed by a `:`, and stop at the first `:` character otherwise. Subjects MAY have whitespace around them.

    @! did:key:z6MkFEB7V...: Object
    @! "Subject": "Object"

The object group is everything in between the `:` that follows the subject, and either the end of the instruction or the `;` that precedes the first parameter. The parser stops collecting the object and starts collecting a bookkeeping line around the first amount it can construe as having a currency unit, if any. It then stops collecting the object or the line when trailing decorators (proofs or capabilities) are all that remains. Objects, lines, and decorators MAY have whitespace around them.

    @! Subject: Object "100" <also:object> '100' +also:object object
    @!    100 Unit <also:unit> +also:unit unit
    @!    <actual:proof> +actual:capability;
    @!    Param 100 <param:param> +param:param = etc.

Directives follow the same rules as actions, with the object prepended with `<` or `>`. Parsers MUST capture the routing or reference directive indicator and continue processing the instruction's object normally, to avoid parsing errors at this stage---constraints on directives get caught later.

    @! Subject: > Object
    @! Subject: < Object <parsed:proof> +parsed:capability


### Reference Version

Apps SHOULD use the Parsing Expression Grammar [or PEG; @Ford2004, @Ford2002] file provided in this section to parse instructions---see Pest in Rust, Peggy in Typescript, CurryLeaf in Swift, BetterParse in Kotlin, Pegasus in .Net, etc.

_Should_ only, because the precise PEG syntax changes from an implementation to the next, and localizing amounts to support different delimiters or non-ASCII digits requires changing the user-facing grammar at display (see Localization Notes, below).

As noted earlier, these specifications' repository [@P2PLedgersRepo] contains a Rust/Pest version of this PEG grammar and a unit-tested parser that takes care of steps 1-7 above---feed it a normalized contract, and it will return a list of parsed instructions or a list of errors. The library is fast, memory safe, and can be compiled to WebAssembly or to a shared library via C-compatible FFI or JNI. It can thus be used as is in most projects.

    # PEG Grammar for Peer-to-Peer Ledger Instructions
    # ================================================
    # Target: Pest, Peggy, or any standard PEG parser.
    # Expects normalized, pre-processed instructions with `@!` stripped
    # continuations joined.
    
    # Main
    Instruction <-  _* subject _* ":"
                    (_* directive)?
                    _* object (_+ line)? (_+ decorator)*
                    (_* ";" _* parameter)*
                    _* EOL?
    
    # Utils
    _           <-  [ \t]                       # Whitespace
    EOL         <-  "\r\n" / "\n" / "\r" / !.   # Tolerate CRLF/CR
    STOP        <-  ";"/ EOL                    # End of Object/Parameter
    quoted      <-  "'" ("''" / (!"'" .))* "'"  # Single quoted
                  / '"' ('""' / (!'"' .))* '"'  # Double quoted
    ID          <-  [a-zA-Z0-9_.-]              # Base64url ID chars
    DID         <-  "did:key:" ID+
    CID         <-  "cid:" ID+
    
    # ISO8601
    # ISO dates seldom get displayed to end-users, so are not localizable.
    ISO8601     <-  iso_date (time_sep iso_time)?
    
    iso_date    <-  year "-" month "-" day
    year        <-  [0-9] [0-9] [0-9] [0-9]
    month       <-  "0" [1-9] / "1" [0-2]
    day         <-  "0" [1-9] / [1-2] [0-9] / "3" [0-1]
    
    time_sep    <-  [Tt ]
    
    iso_time    <-  hour ":" minute (":" second)? microsecs? timezone?
    hour        <-  [0-1] [0-9] / "2" [0-3]
    minute      <-  [0-5] [0-9]
    second      <-  [0-5] [0-9]
    microsecs   <-  [,.] [0-9]+
    timezone    <-  [Zz] / ([+-] hour (":"? minute)?)
    
    # Subject
    subject     <-  quoted
                  / &(DID _* ":") DID
                  / (!":" .)*
    
    # Directive
    directive   <-  ("<" / ">")
    
    # Object
    object      <-  quoted
                  / (!((_+ line)? object_tail) .)*
    object_tail <-  (_+ decorator)* _* STOP
    
    # Line
    line        <-  ISO (_+ prefixed)? _* amount (!(_* ISO) _* suffixed)?
                  / prefixed _* amount (_* (ISO / suffixed (_+ ISO)?))?
                  / amount (_* (ISO / suffixed (_+ ISO)?) &object_tail
                          / _+ unit)
    
    # Localization (Default: +1_000.00)
    sign        <-  [+-]
    zero        <-  "0"
    non_zero    <-  [1-9]
    digit       <-  [0-9]
    digi_sep    <-  "_"
    deci_sep    <-  "."
    
    # Amount
    amount      <-  sign? ("." decimals
                         / integers (deci_sep decidash
                                   / dash
                                   / &infixed infixed decidash)?)
    
    integers    <-  non_zero (digi_sep? digit)* / zero
    decimals    <-  digit (digi_sep? digit)*
    decidash    <-  decimals / dash
    dash        <-  "-"
    
    # Unit
    ISO         <-  [A-Z][A-Z][A-Z] &word_stop
    prefixed    <-  ([A-Z] [A-Z]? "$"
                  / [A-Z] "/" "."?
                  / word_cons word_cons "."?
                  / word_char) &word_stop
    infixed     <-  word_char &(digit / dash)
    suffixed    <-  word_char (("."? word_char)* "."?)?
    
    # Prefixed/Infixed patterns:
    # - [^0-9.]{1,3}                      # $ Fr S/ US$ U$
    # - [^0-9.]{2}[.]                     # B/. Fr.
    # Suffixed patterns:
    # - [^0-9.]{1,3}                      # $ Fr S/
    # - [^0-9.]{2,3}[.]                   # B/. Fr. Dhs.
    # - [^0-9.][.][^0-9.][.]?             # Arabic abbrevs
    # - ([^0-9.]{2}[.]){2}                # Sh.So.
    # - [^0-9.]{4,}                       # USDT MOP$ crvUSD
    word_cons   <-  ![AEIOUaeiou] [A-Za-z]
    word_char   <-  !word_stop .
    word_stop   <-  _ / ['";:<>.0-9+-] / digit / sign / STOP
    
    unit        <-  quoted
                  / (!object_tail .)+
        
    # Decorators
    decorator   <-  proof / capability
    deco_part   <-  (![;+:<>$] .)*
    
    # Proofs
    proof       <-  "<" _* scheme _* ":" _* locator proof_args? _* ">"
    scheme      <-  quoted
                  / (&(DID _* ":") DID)
                  / deco_part
    locator     <-  quoted
                  / (&(CID _* (">" / "$")) CID)
                  / deco_part
    proof_args  <-  (proof_date proof_query? / proof_query proof_date?)
    proof_date  <-  _* "$" _* date
    date        <-  (&(("-" _*)? ISO8601 _* (">" / "$")) deco_part)
    proof_query <-  _* "$" _* query
    query       <-  quoted
                  / deco_part
    
    # Capabilities
    capability  <-  "+" cap_base (":" cap_tail)?
    cap_part    <-  quoted
                  / deco_part
    cap_tail    <-  cap_part &(_ / STOP)
    cap_base    <-  cap_part ":" cap_part (!(":" cap_tail) ":" cap_part)*
    
    # Parameters
    parameter   <-  param_name (_* "=" _* param_value)?
    param_name  <-  quoted
                  / (!(_* (STOP / "=")) .)*
    param_value <-  quoted
                  / (!(_* STOP) .)*

Vendors who prompt an LLM to convert the grammar must mind that LLMs routinely lie and gaslight. This author has seem LLMs volunteer unrequested changes over preposterous claims of non-idiomatic expressions (look-aheads are idiomatic), left recursion (there is none), unsupported constructs (they're all idiomatic), the parser not being capable of expressing the grammar in one pass (the parser can), and backtracking issues (there are none). The worst LLMs go on to report invalid bugs to justify themselves.


### Localization Notes

Vendors that are looking into customizing the parser for localization will want to normalize (see Normalization) the contract first. Then, process instructions one at a time, and aim to retain end-user formatting and original continuations each time to avoid confusion. Mind that the grammar expects instructions with no at-bang and continuations pre-processed (see Parsing Rules, steps 1-3). Also mind that your code must not add unwanted invisible characters that would need to be re-normalized.

For the rest, the general idea is to take what's on the screen, normalize, and parse with the localized grammar to convert amounts to computer format: ASCII digits with `_` and `.` as digit and decimal separators, and units before or after if you toy with infixed units. Store the result for gossiping. That way, you can parse and convert back to the user's prefs for display, and other users will be able to use the shared file with their own localization preferences.

The sign, digits, and separators are all defined for localization purposes, so customizing those is simple, and magnitudes are taken care of by unit clusters (see Unit Clusters).
