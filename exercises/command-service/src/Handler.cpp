#include "Handler.hpp"

// [Implementation 6-1] Map valid requests to store operations

Response PutHandler::handle(const Request &request, Store &store) const {
    store.putNew(request.arguments[0], request.arguments[1]);
    return Response(Response::Ok);
}

Response GetHandler::handle(const Request &request, Store &store) const {
    Response response(Response::NotFound);
    if (store.get(request.arguments[0], response.value))
        response.code = Response::Value;
    return response;
}

Response DeleteHandler::handle(const Request &request, Store &store) const {
    return Response(store.erase(request.arguments[0])
        ? Response::Deleted
        : Response::NotFound);
}

Response CountHandler::handle(const Request &request, Store &store) const {
    static_cast<void>(request);
    Response response(Response::Count);
    response.count = store.size();
    return response;
}

Response ListHandler::handle(const Request &request, Store &store) const {
    static_cast<void>(request);
    Response response(Response::Listing);
    response.entries = store.entries();
    return response;
}

Response QuitHandler::handle(const Request &request, Store &store) const {
    static_cast<void>(request);
    static_cast<void>(store);
    return Response(Response::Bye);
}
