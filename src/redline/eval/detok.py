"""Turn tokenised M2 text back into normal text, keeping each token's character span.

The tools are compared on normal text: LanguageTool would flag "do n't" and "word ." as errors,
which would be unfair to it.
"""

NO_SPACE_BEFORE = {".", ",", ";", ":", "!", "?", ")", "]", "}", "%", "n't", "'s", "'re", "'ve",
                   "'d", "'ll", "'m", "'S", "N'T", "...", "”", "’"}
NO_SPACE_AFTER = {"(", "[", "{", "$", "“", "‘"}


def detokenize(tokens: list[str]) -> tuple[str, list[tuple[int, int]]]:
    parts: list[str] = []
    offsets: list[tuple[int, int]] = []
    pos = 0
    glue_next = True  # no space before the first token
    open_quote = False
    for tok in tokens:
        space = not glue_next
        glue_next = False
        if tok in NO_SPACE_BEFORE:
            space = False
        elif tok == '"':
            if open_quote:
                space = False
            else:
                glue_next = True
            open_quote = not open_quote
        if tok in NO_SPACE_AFTER:
            glue_next = True
        if space:
            parts.append(" ")
            pos += 1
        parts.append(tok)
        offsets.append((pos, pos + len(tok)))
        pos += len(tok)
    return "".join(parts), offsets
