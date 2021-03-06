import { useEffect, useState } from "react";
import axios from "axios";
import {
    Avatar,
    Stack,
    Paper,
    Typography,
    Link,
    Container,
    Box,
    Skeleton
} from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function Groups(props) {
    const [groups, setGroups] = useState(null);
    const navigate = useNavigate();
    const [roomId, setRoomId] = useState(null);

    const updateGroupId = (id) => {
        setRoomId(id);
    };

    useEffect(()=>{

        if (roomId && props.room === roomId) {
            navigate("/chat/");
        }
    })

    useEffect(() => {
        if (roomId !== null && roomId !== undefined) {
            axios({
                method: "POST",
                url: "/api/check_room",
                data: { groupId: roomId },
                headers: {
                    Authorization: "Bearer " + props.token,
                },
            })
                .then((response) => {
                    props.setRoom(roomId);
                })
                .catch((error) => {
                    console.log(error);
                });
        }
    }, [roomId, props]);

    useEffect(() => {
        //gets list of groups
        props.setRoom(null);
        axios({
            method: "GET",
            url: "/api/grouplist",
            headers: {
                Authorization: "Bearer " + props.token,
            },
        })
            .then((response) => {
                const res = response.data;
                setGroups(res);
            })
            .catch((error) => {
                if (error.response) {
                    console.log(error.response);
                    console.log(error.response.status);
                    console.log(error.response.headers);
                }
            });
    }, [props]);
    return (
        <Container maxWidth="sm" sx={{ textAlign: "center" }}>
            <Typography variant="h4" color="text.primary" py={2}>
                Conversations
            </Typography>
            <Box sx={{ maxHeight: "80vh", overflow: "auto" }}>
                <Stack spacing={2}>
                    {groups !== null &&
                    groups !== undefined &&
                    groups.length > 0
                        ? groups.map((group, index) => {
                              return (
                                  <Paper key={index}>
                                      <Link
                                          href="#"
                                          p={2}
                                          onClick={() => {
                                              updateGroupId(group.id);
                                          }}
                                          sx={{
                                              display: "flex",
                                              alignItems: "center",
                                              textDecoration: "none",
                                          }}
                                      >
                                          <Avatar
                                              src={group.picturePath}
                                              alt={
                                                  group.name + " group picture"
                                              }
                                          />
                                          <Typography pl={2}>
                                              {group.name.replace(/\b\w/, (c) =>
                                                  c.toUpperCase()
                                              )}
                                          </Typography>
                                      </Link>
                                  </Paper>
                              );
                          })
                        :                         <>
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                        <Skeleton variant="rectangular" height={75} />
                    </>}
                </Stack>
            </Box>
        </Container>
    );
}
