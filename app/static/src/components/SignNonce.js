import React, { useState, useEffect } from 'react';
import { Button, Spinner, Container, Col, Row, Card } from 'react-bootstrap';
//import 'bootstrap/dist/css/bootstrap.min.css';
import { useHistory } from 'react-router-dom';
import {
    connectWallet,
    getCurrentWalletConnected,
    handleClick
  } from "./util/connect.js";

export default function SignNonce() {
  const [walletAddress, setWallet] = useState("");
  const [status, setStatus] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setURL] = useState("");
  const [signature, setSignature] = useState("");
  const history = useHistory();

  useEffect(() => {
    async function fetchData() {
        const { address, status } = await getCurrentWalletConnected();
        setWallet(address);
    }
    fetchData();
  }, []);

  function handleSignNonce() {
      const { address, signature } = handleClick();
      setSignature(signature);
    }


  return walletAddress.length > 0 ? (
      <Container fluid>
        <Row className="justify-content-md-center" >
          <Col xs lg="2"/>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div
              className="Form"
              style={{ display: "flex", justifyContent: "center" }}
            >
              <Card>
                  <Button onClick={handleSignNonce} variant="dark" size="md">
                   Login
                  </Button>
              </Card>
            </div>
          </Col>
          <Col xs lg="2"/>
        </Row>
      </Container>
    ) : (
      <Container fluid>
        <Row className="justify-content-md-center" >
          <Col xs lg="2"/>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div
              className="Form"
              style={{ display: "flex", justifyContent: "center" }}
            >
            Connect to Metamask first!
            </div>
          </Col>
          <Col xs lg="2"/>
        </Row>
      </Container>
    );
}
