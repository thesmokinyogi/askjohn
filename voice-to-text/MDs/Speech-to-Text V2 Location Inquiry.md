

# **Resolving the Google Cloud Speech-to-Text V2 Location Paradox for Chirp Models**

This report provides a comprehensive analysis of the Google Cloud Speech-to-Text (STT) V2 API location requirements, specifically addressing the contradiction encountered when using high-performance models like Chirp in conjunction with regional resource paths and the batch\_recognize method. The analysis clarifies the strict coupling between client configuration and resource naming required for V2, details programmatic model discovery, and offers prescriptive Python implementations for regional operations in 2025\.

## **I. Executive Summary: Resolving the V2 Location Paradox**

### **1.1 The Inherent Regionalization of Speech-to-Text V2 and Chirp**

The Google Cloud Speech-to-Text V2 API was fundamentally designed to meet heightened enterprise security and regulatory needs, focusing specifically on data residency and compliance.1 This architectural evolution moved away from the V1 API’s largely global abstraction toward a strictly regionalized service structure.

The core promise of V2 is data residency, which ensures that resource generation, logging, and data processing remain entirely within designated geographical boundaries (e.g., Singapore, Belgium, or specific US regions).1 This capability is intrinsically tied to the V2 infrastructure.

The Chirp family of models (chirp, chirp\_2, chirp\_3) are Google’s advanced, multilingual, LLM-powered Automatic Speech Recognition (ASR) systems, available exclusively within V2.3 Their General Availability (GA) is strictly limited to specific, announced regions, such as us-central1, europe-west4, and asia-southeast1.3 This limitation confirms that Chirp models are inherently regional offerings. Consequently, any deployment requiring Chirp must utilize the regionalized V2 architecture to access the underlying specialized infrastructure.

### **1.2 Causal Analysis of the $400$ InvalidArgument Contradiction**

The error message, $400$ Expected resource location to be global, but found us-west1 in resource name, signals a validation failure at the network ingress layer rather than an intrinsic requirement for Chirp to be global.7 The system's behavior reflects a configuration mismatch between how the client connects to the service and how the resource path is constructed.

The standard initialization of the Python SpeechClient() often defaults to the global API endpoint (speech.googleapis.com) unless explicitly overridden.8 This global service ingress layer is configured to route traffic destined for general V2 features and standard models (like long) which are allowed to use the global resource path, such as locations/global/recognizers/\_.5

When the global ingress service receives a request that attempts to define a regional resource path (e.g., projects/{P}/locations/us-west1/...), it cannot successfully validate or route that request to the corresponding regional control plane. The global endpoint operates outside of that siloed regional boundary and lacks the necessary internal context to guarantee regional execution or data residency commitments. Therefore, the service rejects the request and defaults to demanding conformance with the path it serves, which is global.7 The failure occurs because the client attempted to use a regional resource name without first establishing a regional network connection. The resolution is the explicit alignment of the client's network endpoint with the resource’s specified region.

### **1.3 Immediate Architectural Resolution for Regional Operations**

The solution to the $400$ error mandates establishing the client connection via the corresponding regional service boundary that matches the desired Recognizer resource location.

To operate successfully with Chirp or any regional V2 resource, the SpeechClient must be initialized using a regional endpoint, formatted as {REGION}-speech.googleapis.com (e.g., us-central1-speech.googleapis.com).2 Subsequently, the Recognizer resource path used in the transcription request must specify the exact matching region (e.g., projects/{P}/locations/us-central1/recognizers/\_).

The following table summarizes the mandatory dependency between client configuration and resource path for V2 operations:

Location Parameter Dependency in Speech V2 API

| Client Endpoint (ClientOptions) | Required Recognizer Path Location ({L}) | Supported Model Capability | Rationale |
| :---- | :---- | :---- | :---- |
| Default (speech.googleapis.com) | global | Standard V2 Models (e.g., long, short) | Uses global routing abstraction; regional models like Chirp are unavailable or fail validation. |
| Regional ({R}-speech.googleapis.com) | Must match regional code ({R}) e.g., us-central1 | Chirp, Chirp 2, Chirp 3, and regional instances of standard models | Required for strict Data Residency guarantees and access to advanced, regionally deployed models. |

## **II. Deep Dive into Speech V2 Architectural Paradigms**

### **2.1 V1 vs. V2: The Transition to Enforced Regionality**

The design evolution from STT V1 to V2 reflects a focus on enterprise requirements, primarily shifting control plane management and execution to the regional level.2 V2 features, such as data residency, support for Customer-Managed Encryption Keys (CMEK), and enhanced logging, necessitate that all processing occurs within geo-fenced infrastructure.1

This design choice establishes a split personality within the V2 API: a simplified global path for generic, non-compliance use cases, and a strictly enforced regional path for specialized or compliance-sensitive features. The allowance for standard V2 models (e.g., long, short) to use the locations/global path via the default client endpoint is a convenience abstraction.5 However, the moment a user requires strict data residency or uses an intrinsically regional model like Chirp, the regional path becomes the only viable option. The architecture demands that developers select their API path based on the most restrictive compliance or model requirement. For Chirp, which is only provisioned in specific regions, the regional path is non-negotiable, thereby forcing the explicit alignment of the endpoint and the resource path.

### **2.2 The Role of the Recognizer Resource in V2**

The introduction of the Recognizer resource in V2 is central to its architectural identity, serving as a persistent, reusable configuration object, unlike the transient configurations used in V1.9

The Recognizer resource name adheres to the format: projects/{project}/locations/{location}/recognizers/{recognizer}.12 The location segment ({location}) is critical because it dictates the specific Google Cloud region where the configuration is stored and, crucially, where the transcription operation will be executed.12

Even when using the implicit Recognizer—where the {recognizer} segment is replaced with an underscore (recognizers/\_) and the configuration is passed in the request body—a valid location path (either locations/global or locations/us-central1, etc.) must still be provided.5 This location path ensures that the underlying service knows which regional compute infrastructure should handle the request and adhere to the associated compliance boundaries.

### **2.3 The Strict Endpoint-Path Enforcement Mechanism**

The underlying service infrastructure rigorously enforces alignment between the client's connection endpoint and the resource path location to prevent accidental data processing that crosses geopolitical boundaries, which would invalidate data residency guarantees.

The ClientOptions object used during SpeechClient initialization is the mechanism that selects the target service boundary.2 By setting api\_endpoint to a regional URL (e.g., us-central1-speech.googleapis.com), the client explicitly routes the request through the designated regional ingress point.

When a regional endpoint is used, the system expects the resource name in the subsequent API calls (like batch\_recognize or recognize) to reference a resource within that same region. If the api\_endpoint is global, the system expects the resource path to be global. If this coupling is violated—as was the case when the global endpoint received a request for a regional resource—the network layer rejects the request, validating that the request is coming through the expected geopolitical pathway. This strict validation is essential because regional infrastructure often handles authentication keys and service configuration unique to that region, ensuring localized service integrity.14

## **III. Comprehensive Analysis of Model Location Requirements**

The location requirement for a Speech-to-Text V2 operation is dictated by the highest constraint imposed by the model or the compliance needs. For Chirp models, this constraint is always regional.

### **3.1 Model Family Location Mapping**

#### **3.1.1 Location requirements for the Chirp family**

The Chirp family of models, including the latest Chirp 3, represents complex, resource-intensive ASR systems utilizing Universal large Speech Models (USM) and LLM technology.5 Google manages the deployment and scale of these models by restricting their availability to specific, strategically provisioned regions.

The original Chirp model, and subsequent versions like Chirp 2, are confirmed available in regions such as us-central1, europe-west4, and asia-southeast1.3 Accessing these models is a **Mandatory Regional** requirement. Attempting to use the model string chirp or chirp\_2 within a locations/global Recognizer path will result in failure because the underlying model infrastructure is simply not provisioned in the abstract global location, even if the API allows the path format for other models.11

#### **3.1.2 Location requirements for general V2 models (long, short, telephony)**

Standard V2 models, such as long, short, and telephony, are generally available across a broader range of regions.15

These general models offer flexibility: they can be used via the locations/global path (using the default global client endpoint) or through a regional path (using a regional client endpoint).5 However, for any application where data residency is a concern, architectural best practice dictates configuring these models regionally. This ensures that the entire service invocation, from request to logging, adheres to the V2 data residency commitment.2

The decision to strictly confine high-performance models like Chirp to regional access points allows Google to control deployment costs and ensure that the specialized infrastructure required for USM and LLM backends is reliably available only where announced, thus guaranteeing service quality for advanced features.

Regional Availability of High-Performance V2 Models (Chirp Family)

| Model Identifier | Key Function | Supported Recognition Methods | Location Requirement | Initial GA Regions (Reference) |
| :---- | :---- | :---- | :---- | :---- |
| chirp | General Multilingual ASR | Recognize, BatchRecognize | Regional (Mandatory) | us-central1, europe-west4, asia-southeast1 4 |
| chirp\_2 | Enhanced Multilingual ASR | Streaming, Recognize, BatchRecognize | Regional (Mandatory) | us-central1, europe-west4, asia-southeast1 3 |
| chirp\_3 | Latest LLM-powered ASR | Streaming, Recognize, BatchRecognize | Regional (Mandatory) | Query Config API for current support 5 |

### **3.2 Differentiation in Recognition Methods**

The user's issue arose during batch\_recognize. This recognition method handles long-form audio (one minute up to eight hours) and executes asynchronously via Long Running Operations (LROs).4

There is no structural difference in location requirements between synchronous (standard) and asynchronous (batch) recognition for the same model string; the model identifier (e.g., chirp) remains consistent.3

However, the architecture of batch operations reinforces the need for strict regional enforcement. Batch processing involves storing input data (often via GCS URIs) and deferred computation results.12 To guarantee data residency, the regional boundary must be enforced not just at the request initiation point but throughout the entire operation's lifecycle, including temporary storage and asynchronous execution. The global entry point cannot provide the necessary regional assurance for LRO integrity, which explains why the validation failure is particularly aggressive when a regional batch request is routed through the default global API endpoint.

## **IV. Dynamic Model and Feature Discovery using the Config API**

### **4.1 Introduction to projects.locations.config.get (SDK: client.get\_config)**

Given that model availability, language support, and features evolve rapidly—as evidenced by the GA announcement for Chirp 2 in 2025 in specific regions 6—relying solely on static documentation is insufficient. The definitive, runtime method for programmatically determining regional capabilities is the projects.locations.config.get API.3

This API provides location metadata detailing the languages, models, and model features available within a specific region.16 The REST endpoint for this resource follows the format: projects/{project}/locations/{location}/config.17 In the Python SDK, this is exposed via the client.get\_config() method.13

### **4.2 Python Implementation for Programmatic Regional Query**

Successful querying of regional capabilities requires adherence to the V2 architectural principle of regional client binding. The client used to query the configuration must be initialized to the regional endpoint matching the configuration resource name.

Python

from google.cloud.speech\_v2 import SpeechClient  
from google.api\_core.client\_options import ClientOptions  
from google.cloud.speech\_v2.types import GetConfigRequest  
import os

PROJECT\_ID \= os.getenv("GOOGLE\_CLOUD\_PROJECT", "your-project-id")

def get\_regional\_config(project\_id: str, location: str):  
    """  
    Retrieves the configuration object for a specific Speech-to-Text V2 region.  
    Requires client initialization to the corresponding regional endpoint.  
    """  
    try:  
        \# 1\. Initialize client with regional endpoint  
        \# This aligns the network path with the requested resource location.  
        client \= SpeechClient(  
            client\_options=ClientOptions(  
                api\_endpoint=f"{location}\-speech.googleapis.com",  
            )  
        )  
    except Exception as e:  
        print(f"Failed to initialize client for {location}: {e}")  
        return None  
          
    \# 2\. Define the config resource name  
    config\_name \= f"projects/{project\_id}/locations/{location}/config"  
      
    request \= GetConfigRequest(name=config\_name)  
      
    \# 3\. Call the API  
    try:  
        config\_response \= client.get\_config(request=request)  
        print(f"Successfully retrieved config for {location}.")  
        return config\_response  
    except Exception as e:  
        \# Catches errors like 404 (location invalid) or permission errors.  
        print(f"Error retrieving config for {location}: {e}")  
        return None

\# Example Usage:  
\# us\_central\_config \= get\_regional\_config(PROJECT\_ID, "us-central1")  
\# print(us\_central\_config)

### **4.3 Deconstructing the Config Response Object**

The response body from client.get\_config() contains an instance of the Config object (google.cloud.speech\_v2.types.Config).17 While the detailed programmatic schema is typically found within the SDK documentation (e.g., Java documentation references a Config class 19), the API’s stated purpose mandates that the object structure must contain specific metadata to fulfill its function of detailing regional capabilities.16

The Config object establishes the formal contract of capabilities for that region. Since the RecognitionConfig object relies on fields like model and language\_codes 20, the Config response must provide structured data that validates the availability of these specific parameters within the regional scope. It is inferred that the object contains a key complex field that lists supported capabilities.

Inferred Config Response Schema Key Fields for Model Discovery

| Field Name | Type | Description & Relevance to Model Discovery |
| :---- | :---- | :---- |
| name | string | The full resource name of the Config object (projects/{P}/locations/{L}/config). |
| kms\_key\_name | string | Optional: Information regarding Customer-Managed Encryption Keys (CMEK). |
| model\_data | repeated list of objects | **Critical:** Structured list detailing available models (e.g., chirp\_2, telephony), their supported language codes (BCP-47), and recognition features (e.g., diarization, adaptation) within the specified location.15 |
| supported\_features | repeated string | General V2 features supported by the region (e.g., transcript normalization, adaptation). |

Programmatic inspection of the model\_data field within the Config object allows an application to dynamically determine, at runtime, if a given model (like chirp) and its necessary features are provisioned in a particular region. This function prevents configuration errors and facilitates robust regional routing policies.

## **V. Implementation Guide: Deploying Regional Recognizers in Python**

This section provides the necessary Python steps to correctly configure the client and resource path, thereby resolving the $400$ routing error for batch\_recognize using the Chirp model.

### **5.1 Correct SpeechClient Initialization for Regional Access**

The use of ClientOptions to override the default global endpoint is the essential first step for any regional V2 operation, especially when using Chirp.

Python

import os  
from google.api\_core.client\_options import ClientOptions  
from google.cloud.speech\_v2 import SpeechClient  
from google.cloud.speech\_v2.types import cloud\_speech 

PROJECT\_ID \= os.getenv("GOOGLE\_CLOUD\_PROJECT", "your-project-id")  
REGION \= "us-central1" \# Must be a region where Chirp is supported, e.g., us-central1 

\# 1\. Instantiate the client pointing to the specific regional endpoint.  
\# This ensures that all subsequent requests are routed through the regional service boundary.  
try:  
    client \= SpeechClient(  
        client\_options=ClientOptions(  
            api\_endpoint=f"{REGION}\-speech.googleapis.com",   
        )  
    )  
    print(f"SpeechClient initialized for regional endpoint: {REGION}\-speech.googleapis.com")  
except Exception as e:  
    print(f"Client Initialization Error: {e}")

The region in the client endpoint **must match** the location in the Recognizer path. If the endpoint is configured regionally (e.g., us-central1), the request will be successfully routed, and the service will then expect a recognizer path containing locations/us-central1.

### **5.2 Creating an Explicit Regional Recognizer for Chirp**

While implicit recognizers (recognizers/\_) can be used, defining an explicit, named Recognizer is recommended for production environments as it simplifies configuration reuse and tracking.9 The parent path for creation must contain the target region.

Python

def create\_regional\_chirp\_recognizer(client: SpeechClient, project\_id: str, region: str, recognizer\_id: str):  
    """Creates a Recognizer resource scoped to the specified region."""  
      
    parent\_path \= f"projects/{project\_id}/locations/{region}"  
      
    \# Define the configuration using the regional Chirp model  
    config \= cloud\_speech.RecognitionConfig(  
        auto\_decoding\_config=cloud\_speech.AutoDetectDecodingConfig(),  
        language\_codes=,  
        model="chirp", \# Use the regionally supported model  
    )  
      
    request \= cloud\_speech.CreateRecognizerRequest(  
        parent=parent\_path,   
        recognizer\_id=recognizer\_id,  
        recognizer=cloud\_speech.Recognizer(  
            display\_name=f"Chirp Recognizer in {region}",  
            default\_recognition\_config=config,  
        ),  
    )  
      
    \# The client (initialized regionally in 5.1) sends the request to the regional service.  
    operation \= client.create\_recognizer(request=request)  
    recognizer \= operation.result()  
    print(f"Created Regional Recognizer: {recognizer.name}")  
    return recognizer.name

\# Example:  
\# regional\_recognizer\_name \= create\_regional\_chirp\_recognizer(client, PROJECT\_ID, REGION, "my-chirp-batch-recognizer")

### **5.3 Executing BatchRecognize with Regional Resource References**

The final BatchRecognize request uses the fully qualified regional name of the Recognizer. Because the client was initialized with the matching regional endpoint (Section 5.1), the request is successfully routed and validated by the regional service boundary, resolving the initial $400$ error.

Python

def run\_regional\_batch\_recognize(client: SpeechClient, recognizer\_name: str, gcs\_uri: str):  
    """Runs a batch recognition request using a specific regional recognizer."""  
      
    request \= cloud\_speech.BatchRecognizeRequest(  
        recognizer=recognizer\_name,  
        files=,  
    )  
      
    print(f"Starting Batch Recognize using regional recognizer: {recognizer\_name}")  
      
    \# The regionally-bound client executes the request.  
    operation \= client.batch\_recognize(request=request)   
      
    print("Waiting for batch operation to complete...")  
    result \= operation.result()  
    print("Batch operation completed.")  
    return result

## **VI. Conclusion and Architectural Recommendations**

### **6.1 Final V2 Location Rules Summary: The Global Exception**

The core contradiction identified by the user—the error demanding a global location when using a regional model like Chirp—is definitively resolved as a networking and validation failure. The error message is not a rule for Chirp, but a signal that the global API gateway failed to route a regional resource request and defaulted to expecting the path it serves.

For Chirp and any other advanced or compliance-focused model in V2, the following rule holds: The resource location must be regional, and this regional location must be mirrored in the client’s api\_endpoint configuration. The allowance for locations/global is a convenience path for standard V2 models when compliance is not a concern; it is functionally incompatible with Chirp’s underlying infrastructure.

### **6.2 Recommendations for Multi-Region, Multi-Model Deployments**

For applications requiring flexibility across regions and models, adopting a dynamic approach is critical to future-proof the architecture against regional rollouts of advanced models like Chirp 3\.

1. **Mandatory Dynamic Routing with get\_config():** The application should leverage the client.get\_config() API (Section IV) at startup or initialization to build a runtime map of available models, features, and languages per region. This data should serve as the authoritative decision layer for request routing. This step prevents potential failures (such as a $404$ Not Found error) that would occur if a developer manually configured a client to a region that does not yet support a requested model.  
2. **Explicit Client Configuration:** Never rely on the default global client initialization when interacting with V2 features. All V2 interactions should be controlled by explicit environment configuration (e.g., defining SPEECH\_V2\_REGION environment variables) to ensure the client is always initialized with ClientOptions(api\_endpoint=f"{REGION}-speech.googleapis.com").  
3. **Use Explicit Recognizers:** For long-running or batch operations, explicit, named Recognizers are preferred within the regional boundary. This provides better telemetry, simpler configuration management, and clearer resource scoping for data residency audits.

Adherence to these regional architectural principles ensures stability and compliance, recognizing that the V2 API’s strict location constraints are an intentional design feature supporting enterprise-grade services. Programmatic discovery via the Config API is the operational requirement that future-proofs the application against the continuous evolution of Google's multilingual ASR capabilities.

#### **Works cited**

1. Speech-to-Text API: speech recognition and transcription \- Google Cloud, accessed November 11, 2025, [https://cloud.google.com/speech-to-text](https://cloud.google.com/speech-to-text)  
2. Migrating from Speech-to-Text v1 to v2 \- Google Cloud Documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/migration](https://docs.cloud.google.com/speech-to-text/v2/docs/migration)  
3. Chirp 2: Enhanced multilingual accuracy | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/chirp\_2-model](https://docs.cloud.google.com/speech-to-text/v2/docs/chirp_2-model)  
4. Chirp: Universal speech model | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/chirp-model](https://docs.cloud.google.com/speech-to-text/v2/docs/chirp-model)  
5. Compare transcription models | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/transcription-model](https://docs.cloud.google.com/speech-to-text/v2/docs/transcription-model)  
6. Speech-to-Text release notes | Google Cloud Documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/docs/release-notes](https://docs.cloud.google.com/speech-to-text/docs/release-notes)  
7. Not able to use "us-central1" with Chirp · Issue \#11867 · googleapis ..., accessed November 11, 2025, [https://github.com/googleapis/google-cloud-python/issues/11867](https://github.com/googleapis/google-cloud-python/issues/11867)  
8. Class SpeechClient (2.34.0) | Python client libraries | Google Cloud Documentation, accessed November 11, 2025, [https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech\_v1.services.speech.SpeechClient](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v1.services.speech.SpeechClient)  
9. Recognizers | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/recognizers](https://docs.cloud.google.com/speech-to-text/v2/docs/recognizers)  
10. Google speech v2: 'Expected resource location to be global, but found europe-west4 in resource name.', \- Stack Overflow, accessed November 11, 2025, [https://stackoverflow.com/questions/77076285/google-speech-v2-expected-resource-location-to-be-global-but-found-europe-wes](https://stackoverflow.com/questions/77076285/google-speech-v2-expected-resource-location-to-be-global-but-found-europe-wes)  
11. google cloud platform \- Speech to text chirp model issue in c\# ..., accessed November 11, 2025, [https://stackoverflow.com/questions/77124941/speech-to-text-chirp-model-issue-in-c-sharp](https://stackoverflow.com/questions/77124941/speech-to-text-chirp-model-issue-in-c-sharp)  
12. Method: projects.locations.recognizers.recognize | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.recognizers/recognize](https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.recognizers/recognize)  
13. Class SpeechClient (2.34.0) | Python client libraries | Google Cloud Documentation, accessed November 11, 2025, [https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech\_v2.services.speech.SpeechClient](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.services.speech.SpeechClient)  
14. Speech service supported regions \- Azure \- Microsoft Learn, accessed November 11, 2025, [https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions)  
15. Speech-to-Text V2 supported languages \- Google Cloud Documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/speech-to-text-supported-languages](https://docs.cloud.google.com/speech-to-text/v2/docs/speech-to-text-supported-languages)  
16. Regional availability | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://docs.cloud.google.com/speech-to-text/v2/docs/locations](https://docs.cloud.google.com/speech-to-text/v2/docs/locations)  
17. Method: projects.locations.config.get | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.config/get](https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.config/get)  
18. Method: projects.locations.config.update | Cloud Speech-to-Text V2 documentation, accessed November 11, 2025, [https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.config/update](https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/projects.locations.config/update)  
19. com.google.cloud.speech.v2 \- Java client library | Google Cloud, accessed November 11, 2025, [https://cloud.google.com/java/docs/reference/google-cloud-speech/latest/com.google.cloud.speech.v2](https://cloud.google.com/java/docs/reference/google-cloud-speech/latest/com.google.cloud.speech.v2)  
20. Cloud Speech V2 Client \- Class RecognitionConfig (2.2.1) | PHP client libraries, accessed November 11, 2025, [https://docs.cloud.google.com/php/docs/reference/cloud-speech/latest/V2.RecognitionConfig](https://docs.cloud.google.com/php/docs/reference/cloud-speech/latest/V2.RecognitionConfig)  
21. Class RecognitionConfig (2.33.0) | Python client library | Google Cloud, accessed November 11, 2025, [https://cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech\_v2.types.RecognitionConfig](https://cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.types.RecognitionConfig)