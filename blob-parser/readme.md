# Blob Parser

Blob parser parses the HTML from the Blob Storage into JSON for the cosmos DB.
It then inserts the data into the DB.

Note that this function produces a lot of output after starting the function app, because it is continuously checking for its trigger. For this reason, you may want to disable this function during local development if it's not needed. To do this, click the 'A' in VS Code sidebar, find the function at the bottom under Workspace > Local Project > Functions, right-click on it and click Disable. You can use the same menu to re-enable it when you need it again.

Triggered by blob storage.

## Implementation Details

The `BlobTrigger` makes it incredibly easy to react to new Blobs inside of Azure Blob Storage. This sample demonstrates a simple use case of processing data from a given Blob using Python.

For a `BlobTrigger` to work, you provide a path which dictates where the blobs are located inside your container, and can also help restrict the types of blobs you wish to return. For instance, you can set the path to `samples/{name}.png` to restrict the trigger to only the samples path and only blobs with ".png" at the end of their name.
