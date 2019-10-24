import React, { MouseEvent, useEffect, useState } from "react";
import Token from "./Token";
import dwarf from "../icon/dwarf.svg";
import bear from "../icon/bear.svg";
import wall from "../icon/wall.svg";
import { List } from "immutable";
import { makeStyles } from "@material-ui/core";
import { GRID_SIZE_PX } from "../config";
import TokenSheet, { TokenType } from "./TokenSheet";
import { Token as TokenState } from "../network/TokenStateClient";
import uuid from "uuid";
import { WallType } from "./WallSheet";

let BACKGROUND_COLOR = "#F5F5DC";
let GRID_COLOR = "#947C65";

const snapToGrid = (x: number) => Math.round(x / GRID_SIZE_PX) * GRID_SIZE_PX;

const useStyles = makeStyles({
  map: {
    backgroundColor: BACKGROUND_COLOR,
    backgroundImage: `repeating-linear-gradient(
      0deg,
      transparent,
      transparent ${GRID_SIZE_PX - 1}px,
      ${GRID_COLOR} ${GRID_SIZE_PX - 1}px,
      ${GRID_COLOR} ${GRID_SIZE_PX}px
    ),
    repeating-linear-gradient(
      -90deg,
      transparent,
      transparent ${GRID_SIZE_PX - 1}px,
      ${GRID_COLOR} ${GRID_SIZE_PX - 1}px,
      ${GRID_COLOR} ${GRID_SIZE_PX}px
    )`,
    backgroundSize: `${GRID_SIZE_PX}px ${GRID_SIZE_PX}px`,
    height: "100%",
    width: "100%",
    position: "absolute",
    // All the tokens inside the map have to be position absolute so that the
    // drag offset calculations work properly
    "& div": {
      position: "absolute"
    }
  },
  sheets: {
    display: "flex",
    flexDirection: "column",
    maxWidth: GRID_SIZE_PX * 2,
    position: "absolute",
    bottom: 0
  }
});

const TOKEN_TYPES = [
  { id: "a511ebd2-827b-490d-b20a-c206e4edd25e", icon: bear },
  { id: "643c7cf8-befb-4a72-b707-9c0399d2a365", icon: dwarf }
];

const App = () => {
  const classes = useStyles();
  const [socket, setSocket] = useState();

  useEffect(() => {
    const registerWebsocket = async () => {
      const resp = await fetch("http://192.168.0.105:5000/api/socket");
      const json = await resp.json();
      const socketUrl = json.path;
      const socket = new WebSocket(socketUrl);

      socket.addEventListener("open", (event: Event) => {
        console.log("Connected");
      });

      socket.addEventListener("message", (event: MessageEvent) => {
        const newTokens = JSON.parse(event.data);
        console.log(newTokens);
        setTokens(List.of(...newTokens));
      });

      socket.addEventListener("error", (event: Event) => {
        console.log("Failed to connect");
        console.log(event);
      });

      setSocket(socket);
    };

    // noinspection JSIgnoredPromiseFromCall
    registerWebsocket();
  }, []);

  const [tokens, setTokens] = useState(List.of<TokenState>());
  const [activeWallType, setWallType] = useState();

  const onTokenPlaced = (type: TokenType, x: number, y: number) => {
    let token = {
      id: uuid(),
      x: snapToGrid(x),
      y: snapToGrid(y),
      icon: type.icon
    };
    if (socket && socket.readyState === socket.OPEN) {
      socket.send(
        JSON.stringify({
          action: "create",
          data: token
        })
      );
    }
    setTokens(tokens.push(token));
  };

  const onWallTypeSelected = (type?: WallType) => {
    setWallType(type);
  };

  const tokenIcons = tokens.map((token, i) => (
    <Token
      pos={{ x: token.x, y: token.y }}
      icon={token.icon}
      key={token.id}
      onDropped={(x, y) => {
        const newToken = {
          id: token.id,
          x: snapToGrid(x),
          y: snapToGrid(y),
          icon: token.icon
        };
        if (socket && socket.readyState === socket.OPEN) {
          socket.send(
            JSON.stringify({
              action: "update",
              data: newToken
            })
          );
        }
        setTokens(tokens.set(i, newToken));
      }}
    />
  ));

  const onMapClick = (e: MouseEvent) => {
    if (activeWallType) {
      tokens.push({
        id: uuid(),
        x: snapToGrid(e.clientX),
        y: snapToGrid(e.clientY),
        icon: wall
      });
    }
  };

  const onMapRightClick = (e: MouseEvent) => {
    e.preventDefault();
    const x = Math.floor(e.clientX / GRID_SIZE_PX) * GRID_SIZE_PX;
    const y = Math.floor(e.clientY / GRID_SIZE_PX) * GRID_SIZE_PX;
    for (const [i, token] of tokens.entries()) {
      if (token.x === x && token.y === y) {
        socket.send(JSON.stringify({
          action: "delete",
          data: { id: token.id }
        }));

        setTokens(tokens.delete(i));
      }
    }
  };

  return (
    <div>
      <div
        className={classes.map}
        onClick={onMapClick}
        onContextMenuCapture={onMapRightClick}
      >
        {tokenIcons}
      </div>
      <div className={classes.sheets}>
        <TokenSheet tokenTypes={TOKEN_TYPES} onTokenPlaced={onTokenPlaced} />
      </div>
    </div>
  );
};

export default App;