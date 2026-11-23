"""
WhatsApp Cloud API integration: the chat engine behind a WhatsApp number.

    client.py      signature check, send a text reply
    formatting.py  markdown -> WhatsApp markup, message splitting
    repository.py  SQL: number -> domain mapping, dedupe, lead row
    service.py     handle one webhook delivery
    __main__.py    `python -m whatsapp add|list` to register numbers

The route itself is api/whatsapp.py.
"""
