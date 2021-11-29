// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./ERC721Tradable.sol";


contract LaunchCollectible is ERC721Tradable {

    constructor(address _proxyRegistryAddress)
        ERC721Tradable("Chainlink Fall Hackathon 2021", "HACK", _proxyRegistryAddress) {}

    function getTokenURI(uint256 tokenId) public view returns (string memory) {
        return tokenURI(tokenId);
    }

    function setTokenURI(uint256 tokenId, string memory _tokenURI) public {
        require(
            _isApprovedOrOwner(_msgSender(), tokenId),
            "ERC721: transfer caller is not owner nor approved"
        );
        setTokenURI(tokenId, _tokenURI);
    }

    function baseTokenURI() override public pure returns (string memory) {
        return "https://gateway.pinata.cloud/ipfs/";
    }

    function contractURI() public pure returns (string memory) {
        return "https://gateway.pinata.cloud/ipfs/";
    }

}
