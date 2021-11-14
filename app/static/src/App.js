import React, { Component } from 'react';
import ReactDOM from "react-dom";
import Connect from './components/Connect';
import SignNonce from './components/SignNonce';
import { DAppProvider } from "@usedapp/core";

class App extends Component {
  render() {
    return (
      <DAppProvider config={{}}>
        <div>
          <Connect />
          <SignNonce />
        </div>
      </DAppProvider>
    );
  }
}

export default App;
