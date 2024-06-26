# Welcome to MkDocs

For full documentation visit [mkdocs.org](https://www.mkdocs.org){ data-preview }

[Attribute Lists](api.md#files_file_createcontext-context-data_dict-dictstr-any-dictstr-any){ data-preview }


!!! note "Some title"

Some content

!!! abstract "Some title"

Some content


??? tip "Open styled details"

??? danger "Nested details!"
And more content again.


``` yaml
theme:
features:
- content.code.annotate # (1)!
```

1.  :man_raising_hand: I'm a code annotation! I can contain `code`, __formatted
text__, images, ... basically anything that can be written in Markdown.

=== "C"

``` c
#include <stdio.h>

int main(void) {
printf("Hello world!\n");
return 0;
}
```

=== "C++"

``` c++
#include <iostream>

int main(void) {
std::cout << "Hello world!" << std::endl;
return 0;
}
```

``` mermaid
graph LR
A[Start] --> B{Error?};
B -->|Yes| C[Hmm...];
C --> D[Debug];
D --> B;
B ---->|No| E[Yay!];
```

``` mermaid
sequenceDiagram
autonumber
Alice->>John: Hello John, how are you?
loop Healthcheck
John->>John: Fight against hypochondria
end
Note right of John: Rational thoughts!
John-->>Alice: Great!
John->>Bob: How about you?
Bob-->>John: Jolly good!
```

```py title="IFiles"
-8<- "ckanext/files/interfaces.py:interface"

      ```

      === "Hello"

      world

      === "bye"

      world
