package dev.guides.spring.boundaries;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class PreviewControllerTest {
  @Autowired MockMvc mvc;

  @Test
  void acceptsRequestInsidePolicy() throws Exception {
    mvc.perform(post("/requests/preview")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"quantity\":10,\"category\":\"STANDARD\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.accepted").value(true));
  }

  @Test
  void rejectsInvalidQuantityAsBadRequest() throws Exception {
    mvc.perform(post("/requests/preview")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"quantity\":0,\"category\":\"STANDARD\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.errorCode").value("INVALID_REQUEST"))
        .andExpect(jsonPath("$.fields.quantity").exists());
  }

  @Test
  void rejectsBusinessPolicyAsConflict() throws Exception {
    mvc.perform(post("/requests/preview")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"quantity\":101,\"category\":\"STANDARD\"}"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.errorCode").value("QUANTITY_OUT_OF_RANGE"));
  }
}
