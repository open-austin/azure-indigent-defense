# Message Queue Scrapper

Azure functions time out after 5-10 min. (exact timeout is configured in `host.json`) For this reason, when the http-scraper function hits a day that has a lot of cases, it will write to a message queue instead of scraping them, thus passing the work to this second function and avoiding a timeout.

Note that if you are working with this function, you may want to manually clear the message queue in between test runs, because it will attempt to process old messages left over from previous runs. It will try to process a message 5 times before moving it to the poison queue.

Triggered by new messages in the message queue.

## Implementation Details

The `QueueTrigger` makes it incredibly easy to react to new Queues inside of Azure Queue Storage. This sample demonstrates a simple use case of processing data from a given Queue.

For a `QueueTrigger` to work, you provide a path which dictates where the queue messages are located inside your container.
