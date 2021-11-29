// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;


import "./IFactoryERC721.sol";
import "./LaunchCollectible.sol";

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";

contract Factory is FactoryERC721, Ownable, VRFConsumerBase {
    using SafeMath for uint256;
    using Strings for string;

    bytes32 internal keyHash;
    uint256 internal fee;
    uint256 public randomResult;
    address public vrfCoordinator;
    // rinkeby: 0xb3dCcb4Cf7a26f6cf6B120Cf5A73875B7BBc655B
    address public linkToken;
    // rinkeby: 0x01BE23585060835E02B77ef475b0Cc51aA1e0709a

    struct Launchable {
        uint256 layer1;
        uint256 layer2;
        uint256 layer3;
        uint256 layer4;
        string launchableName;
    }

    Launchable[] public launchables;

    mapping(bytes32 => string) public requestToLaunchable;
    mapping(bytes32 => address) public requestToSender;
    mapping(bytes32 => uint256) public requestToTokenId;

    event Transfer(
        address indexed from,
        address indexed to,
        uint256 indexed tokenId
    );

    address public proxyRegistryAddress;
    address public nftAddress;
    string public baseURI = "https://gateway.pinata.cloud/ipfs/";

    /*
     * Enforce the existence of only 100 OpenSea creatures.
     */

    uint256 collectibleTotalSupply = 100;

    /*
     * Three different options for minting Creatures (basic, premium, and gold).
     */

    uint256 numOptions = 1;
    uint256 singleMint = 0;

    constructor(address _proxyRegistryAddress,
                address _nftAddress,
                address _vrfCoordinator,
                address _linkToken,
                bytes32 _keyHash)
                VRFConsumerBase(_vrfCoordinator, _linkToken)
    {
        proxyRegistryAddress = _proxyRegistryAddress;
        nftAddress = _nftAddress;
        vrfCoordinator = _vrfCoordinator;
        linkToken = _linkToken;
        keyHash = _keyHash;
        fee = 0.1 * 10**18;

        fireTransferEvents(address(0), owner());
    }

    function symbol() override external pure returns (string memory) {
        return "HACK";
    }

    function tokenURI(uint256 _optionId) override external view returns (string memory) {
        return string(abi.encodePacked(baseURI, Strings.toString(_optionId)));
    }

    function name() override external pure returns (string memory) {
        return "austpryb";
    }

    function getNumberOfLaunchables() public view returns (uint256) {
        return launchables.length;
    }

    function requestLaunchable(
        string memory launchableName
    ) public returns (bytes32) { // bytes32
        /*
        require(
            LINK.balanceOf(address(this)) >= fee,
            "Not enough LINK - fill contract with faucet"
        );
        */
        bytes32 requestId = requestRandomness(keyHash, fee);
        requestToLaunchable[requestId] = launchableName;
        requestToSender[requestId] = msg.sender;
        return requestId;
    }

    function supportsFactoryInterface() override public pure returns (bool) {
        return true;
    }
    /**
    function numOptions() override public view returns (uint256) {
        return numOptions;
    }
    */

    function transferOwnership(address newOwner) override public onlyOwner {
        address _prevOwner = owner();
        super.transferOwnership(newOwner);
        fireTransferEvents(_prevOwner, newOwner);
    }

    function mint(uint256 _optionId, address _toAddress) override public {
        // Must be sent from the owner proxy or owner.
        ProxyRegistry proxyRegistry = ProxyRegistry(proxyRegistryAddress);
        assert(
            address(proxyRegistry.proxies(owner())) == _msgSender() ||
                owner() == _msgSender()
        );
        // require(canMint(_optionId));

        LaunchCollectible launchCollectible = LaunchCollectible(nftAddress);
        launchCollectible.mintTo(_toAddress);
    }

    function canMint(uint256 _optionId) override public view returns (bool) {
        if (_optionId >= numOptions) {
            return false;
        }

        LaunchCollectible launchCollectible = LaunchCollectible(nftAddress);

        uint256 collectibleSupply = launchCollectible.totalSupply();

        uint256 numItemsAllocated = 1;

        return collectibleSupply < (collectibleTotalSupply - numItemsAllocated);
    }

    function getLaunchableStats(uint256 tokenId)
        public
        view
        returns (
            uint256,
            uint256,
            uint256,
            uint256
        )
    {
        return (
            launchables[tokenId].layer1,
            launchables[tokenId].layer2,
            launchables[tokenId].layer3,
            launchables[tokenId].layer4
        );
    }

    function transferFrom(
        address _to,
        uint256 _tokenId
    ) public {
        mint(_tokenId, _to);
    }

    /**
     * Hack to get things to work automatically on OpenSea.
     * Use isApprovedForAll so the frontend doesn't have to worry about different method names.
     */
    function isApprovedForAll(address _owner, address _operator)
        public
        view
        returns (bool)
    {
        if (owner() == _owner && _owner == _operator) {
            return true;
        }

        ProxyRegistry proxyRegistry = ProxyRegistry(proxyRegistryAddress);
        if (
            owner() == _owner &&
            address(proxyRegistry.proxies(_owner)) == _operator
        ) {
            return true;
        }

        return false;
    }

    function ownerOf(uint256 _tokenId) public view returns (address _owner) {
        return owner();
    }

    function fulfillRandomness(bytes32 requestId, uint256 randomNumber)
    internal
    override
    {
        uint256 layer1 = (randomNumber % 3);
        uint256 layer2 = (randomNumber % 3);
        uint256 layer3 = (randomNumber % 3);
        uint256 layer4 = (randomNumber % 3);
        uint256 newId = launchables.length;
        requestToTokenId[requestId] = newId;

        launchables.push(
            Launchable(
                layer1,
                layer2,
                layer3,
                layer4,
                requestToLaunchable[requestId]
            )
        );
        mint(newId, requestToSender[requestId]);
    }

    function fireTransferEvents(address _from, address _to) private {
        for (uint256 i = 0; i < numOptions; i++) {
            emit Transfer(_from, _to, i);
        }
    }


}
