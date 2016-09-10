-module(tree_dht).

-export([start_link/0,start/0,stop/0]).
-export([init/0]).
-export([send_hash_message/1]).

%% Management API.

start() ->
    proc_lib:start(?MODULE, init, []).

start_link() ->
    proc_lib:start_link(?MODULE, init, []).

stop() ->
    cast(stop).

%% Server state.

-record(state, {}).

%% User API.

send_hash_message(Message) ->
    cast({send_hash_message,Message}).


%% Internal protocol functions.

cast(Message) ->
    hash_server ! {cast,self(),Message},
    ok.

%% Initialise it all.

init() ->
    io:format("~p ~n", [<<"Donde donde donde">>]),
    application:ensure_all_started(dht),
    % Val = "Carepetch",
    % ID = crypto:hash(sha, Val),
    register(hash_server, self()),
    proc_lib:init_ack({ok,self()}),
    loop(#state{}).

loop(State) ->
    receive
        {cast,From,{send_hash_message,Message}} ->
            io:format("~w: ~p\n", [From,Message]),
            loop(State);
        {cast,_From,stop} ->            %We're done
            ok;
        _ ->                            %Ignore everything else
            loop(State)
    end.