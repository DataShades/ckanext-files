declare var onconnect: any;
onconnect = (event: MessageEvent) => {
    const port = event.ports[0]
    port.onmessage = (e: MessageEvent) => {
    }

}
